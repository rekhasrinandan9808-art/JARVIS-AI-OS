from __future__ import annotations
import asyncio
import logging
import os
import tempfile
import wave
import time
import threading
import queue
import pythoncom
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import numpy as np

from ..base_agent import BaseAgent, AgentCapability

# Load .env
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(), override=False)
except ImportError:
    pass

# Try SAPI (Windows) - Preferred
try:
    import win32com.client
    HAS_SAPI = True
except ImportError:
    HAS_SAPI = False
    logging.warning("SAPI not available. Install: pip install pywin32")

# Fallback TTS
try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Try to import Whisper for local transcription (fallback)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Try to import noisereduce for noise suppression
try:
    import noisereduce as nr
    NOISE_REDUCE_AVAILABLE = True
except ImportError:
    NOISE_REDUCE_AVAILABLE = False
    logging.warning("Noisereduce not available. Install: pip install noisereduce")

logger = logging.getLogger("jarvis.voice")


class VoiceAgent(BaseAgent):
    name = "voice"
    description = "Speech-to-text via Groq Whisper API, TTS via Windows SAPI, with energy-based VAD and noise reduction"
    agent_id = 17

    def __init__(self):
        super().__init__()
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.p = None
        self._is_recording = False
        self._tts_lock = threading.Lock()
        self._sapi_initialized = False
        self.mic_device_index = None
        self.mic_device_name = None

        # Streaming attributes
        self._streaming = False
        self._stream_thread = None
        self._stop_streaming = False
        self._transcription_callback = None
        
        # Energy-based VAD settings (no external dependencies)
        self._sample_rate = 16000
        self._chunk_size = 1024  # 64ms at 16kHz
        self._silence_timeout = 1.5  # seconds of silence before processing
        self._vad_threshold = 0.04  # Increased from 0.015 to reduce noise sensitivity
        self._is_speaking_flag = False  # Track when bot is speaking
        self._noise_profile = None  # For noise reduction
        self._noise_profile_collected = False
        
        # Buffer for speech
        self._speech_buffer = []
        self._silence_counter = 0
        self._is_speaking = False
        self._silence_frames_threshold = int(self._silence_timeout * self._sample_rate / self._chunk_size)
        self._min_speech_frames = int(0.8 * self._sample_rate / self._chunk_size)  # Min 0.8s speech
        
        # Whisper model for fallback
        self._whisper_model = None
        if WHISPER_AVAILABLE:
            try:
                model_size = os.getenv("WHISPER_MODEL", "base.en")
                self._whisper_model = whisper.load_model(model_size)
                logger.info(f"✅ Whisper loaded with model {model_size}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load Whisper: {e}")

        # Initialize SAPI in the main thread
        if HAS_SAPI:
            try:
                pythoncom.CoInitialize()
                self.sapi_speaker = win32com.client.Dispatch("SAPI.SpVoice")
                
                # Get available voices
                voices = self.sapi_speaker.GetVoices()
                for voice in voices:
                    voice_name = voice.GetDescription()
                    if "Zira" in voice_name or "David" in voice_name:
                        self.sapi_speaker.Voice = voice
                        logger.info(f"Using SAPI voice: {voice_name}")
                        break
                
                self.sapi_speaker.Rate = 0
                self.sapi_speaker.Volume = 100
                self._sapi_initialized = True
                logger.info("✅ SAPI TTS initialized")
            except Exception as e:
                logger.error(f"SAPI init error: {e}")
                self.sapi_speaker = None

        # Fallback to pyttsx3
        if not self._sapi_initialized and HAS_TTS:
            try:
                self.fallback_tts = pyttsx3.init()
                logger.info("Fallback TTS initialized")
            except:
                self.fallback_tts = None
        else:
            self.fallback_tts = None

        # Initialize PyAudio and auto-detect microphone
        self._init_microphone()

        # Calculate noise floor and auto-adjust threshold
        self._noise_floor = 0.01
        self._auto_adjust_vad()

        logger.info(f"Groq API key: {'found' if self.groq_api_key else 'MISSING'}")
        logger.info(f"🔊 VAD threshold set to: {self._vad_threshold:.4f}")
        logger.info(f"🔊 Noise reduction: {'✅ Available' if NOISE_REDUCE_AVAILABLE else '❌ Not available'}")

    def _collect_noise_profile(self, duration: float = 2.0):
        """Collect background noise profile for noise reduction."""
        if not NOISE_REDUCE_AVAILABLE or self._noise_profile_collected:
            return
        
        if self.p is None or self.mic_device_index is None:
            return
        
        try:
            logger.info("🔊 Collecting noise profile... (please stay quiet for 2 seconds)")
            
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self.mic_device_index,
                frames_per_buffer=CHUNK
            )
            
            frames = []
            num_chunks = int(RATE / CHUNK * duration)
            for _ in range(num_chunks):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # Convert to numpy array
            audio_data = b''.join(frames)
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Store noise profile
            self._noise_profile = audio_array
            self._noise_profile_collected = True
            
            # Calculate noise floor
            noise_energy = np.sqrt(np.mean(audio_array ** 2))
            self._noise_floor = noise_energy
            
            # Adjust VAD threshold based on noise
            self._vad_threshold = max(noise_energy * 4.0, 0.025)
            
            logger.info(f"🔊 Noise profile collected! Noise floor: {noise_energy:.4f}, VAD threshold: {self._vad_threshold:.4f}")
            
        except Exception as e:
            logger.warning(f"Failed to collect noise profile: {e}")

    def _auto_adjust_vad(self):
        """Auto-adjust VAD threshold based on background noise."""
        if self.p is None or self.mic_device_index is None:
            return
        
        try:
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self.mic_device_index,
                frames_per_buffer=CHUNK
            )
            
            # Read background noise sample
            frames = []
            for _ in range(20):  # Longer sample for better noise estimation
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # Calculate noise floor
            audio_data = b''.join(frames)
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            noise_energy = np.sqrt(np.mean(audio_array ** 2))
            
            # Set threshold to 4x noise floor (with minimum)
            self._vad_threshold = max(noise_energy * 4.0, 0.025)
            self._noise_floor = noise_energy
            
            logger.info(f"🔧 Auto-adjusted VAD threshold to: {self._vad_threshold:.4f} (noise floor: {noise_energy:.4f})")
            
        except Exception as e:
            logger.warning(f"Auto VAD adjustment failed: {e}")

    def _init_microphone(self):
        """Initialize microphone with auto-detection."""
        if not HAS_PYAUDIO:
            logger.warning("PyAudio not available. Install: pip install pyaudio")
            return

        try:
            self.p = pyaudio.PyAudio()
            
            # List all devices
            device_count = self.p.get_device_count()
            logger.info(f"Found {device_count} audio devices")
            
            # Find microphone
            mic_found = False
            for i in range(device_count):
                try:
                    info = self.p.get_device_info_by_index(i)
                    device_name = info.get('name', '').lower()
                    max_input_channels = info.get('maxInputChannels', 0)
                    
                    logger.debug(f"Device {i}: {info.get('name', 'Unknown')} (channels: {max_input_channels})")
                    
                    # Check if it's a microphone (has input channels)
                    if max_input_channels > 0:
                        # Prefer devices with "microphone" or "mic" in name
                        if 'microphone' in device_name or 'mic' in device_name:
                            self.mic_device_index = i
                            self.mic_device_name = info.get('name', f'Microphone {i}')
                            mic_found = True
                            logger.info(f"✅ Found microphone: {self.mic_device_name} (index: {i})")
                            break
                        elif not mic_found:
                            # Fallback to first input device
                            self.mic_device_index = i
                            self.mic_device_name = info.get('name', f'Device {i}')
                            mic_found = True
                            logger.info(f"Using fallback microphone: {self.mic_device_name} (index: {i})")
                except Exception as e:
                    logger.debug(f"Error checking device {i}: {e}")
            
            if not mic_found:
                logger.warning("No microphone found! Using default (index 0)")
                self.mic_device_index = 0
                self.mic_device_name = "Default Microphone"
            
            # Test the microphone
            if self.mic_device_index is not None:
                self._test_microphone()
                
        except Exception as e:
            logger.error(f"Microphone initialization error: {e}")
            self.p = None
            self.mic_device_index = None

    def _test_microphone(self):
        """Test if microphone is working."""
        if self.p is None or self.mic_device_index is None:
            return
        
        try:
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            logger.info(f"Testing microphone: {self.mic_device_name}...")
            
            stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self.mic_device_index,
                frames_per_buffer=CHUNK
            )
            
            # Read a small sample
            data = stream.read(CHUNK, exception_on_overflow=False)
            stream.stop_stream()
            stream.close()
            
            # Check if data has audio (non-zero values)
            import struct
            values = struct.unpack('h' * (len(data) // 2), data)
            max_val = max(abs(v) for v in values)
            
            if max_val > 100:
                logger.info(f"✅ Microphone test passed (signal detected)")
                # Collect noise profile
                self._collect_noise_profile()
            else:
                logger.warning(f"⚠️ Microphone test: weak or no signal (max: {max_val})")
                
        except Exception as e:
            logger.warning(f"Microphone test failed: {e}")

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("speak", "Speak text using SAPI TTS", {"text": "str"}),
            AgentCapability("listen", "Listen and transcribe", {"duration": "int"}),
            AgentCapability("test_mic", "Test microphone", {}),
            AgentCapability("list_devices", "List audio devices", {}),
            AgentCapability("start_streaming", "Start true continuous streaming with VAD", {"callback": "callable"}),
            AgentCapability("stop_streaming", "Stop continuous streaming", {}),
            AgentCapability("is_streaming", "Check if streaming is active", {}),
            AgentCapability("set_vad_threshold", "Set VAD energy threshold", {"threshold": "float"}),
            AgentCapability("collect_noise_profile", "Collect background noise profile", {}),
        ]

    def _apply_noise_reduction(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply noise reduction to audio data."""
        if not NOISE_REDUCE_AVAILABLE or self._noise_profile is None:
            return audio_array
        
        try:
            # Apply noise reduction
            reduced = nr.reduce_noise(
                y=audio_array,
                sr=self._sample_rate,
                y_noise=self._noise_profile,
                prop_decrease=0.8,
                n_fft=1024,
                win_length=1024,
                hop_length=512
            )
            return reduced
        except Exception as e:
            logger.debug(f"Noise reduction failed: {e}")
            return audio_array

    def _energy_detection(self, frame_bytes: bytes) -> bool:
        """
        Energy-based VAD using RMS calculation with noise reduction.
        """
        # If bot is speaking, ignore all input (prevent echo)
        if self._is_speaking_flag:
            return False
        
        try:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Apply noise reduction if available
            if NOISE_REDUCE_AVAILABLE and self._noise_profile is not None:
                audio_data = self._apply_noise_reduction(audio_data)
            
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_data ** 2))
            
            # Check if energy exceeds threshold
            return energy > self._vad_threshold
        except:
            return False

    def start_streaming(self, callback: Callable[[str], None], vad_enabled: bool = True):
        """
        Start true continuous audio streaming with energy-based VAD.
        No fixed recording window - uses VAD to detect speech segments.
        """
        if self._streaming:
            logger.warning("⚠️ Streaming already running")
            return False

        if self.p is None or self.mic_device_index is None:
            logger.error("❌ Microphone not available")
            return False

        self._transcription_callback = callback
        self._stop_streaming = False
        self._streaming = True
        self._speech_buffer = []
        self._silence_counter = 0
        self._is_speaking = False
        
        try:
            # Open stream
            self._stream = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._sample_rate,
                input=True,
                input_device_index=self.mic_device_index,
                frames_per_buffer=self._chunk_size
            )
            
            # Start VAD streaming thread
            self._stream_thread = threading.Thread(
                target=self._vad_streaming_loop,
                daemon=True
            )
            self._stream_thread.start()
            
            logger.info(f"🎤 True continuous streaming started with energy-based VAD")
            logger.info(f"   Threshold: {self._vad_threshold:.4f}, Silence timeout: {self._silence_timeout}s")
            logger.info(f"   Noise reduction: {'✅ Enabled' if NOISE_REDUCE_AVAILABLE else '❌ Disabled'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            self._streaming = False
            return False

    def _vad_streaming_loop(self):
        """True VAD streaming loop using energy detection."""
        logger.info("🔊 VAD streaming loop started")
        
        is_speaking = False
        speech_buffer = []
        silence_counter = 0
        speech_frame_count = 0
        
        while not self._stop_streaming:
            try:
                data = self._stream.read(self._chunk_size, exception_on_overflow=False)
                
                # Check for voice activity using energy detection
                is_speech = self._energy_detection(data)
                
                if is_speech:
                    if not is_speaking:
                        is_speaking = True
                        speech_buffer = []
                        speech_frame_count = 0
                        logger.debug("🔊 Speech started")
                    
                    speech_buffer.append(data)
                    silence_counter = 0
                    speech_frame_count += 1
                    
                else:
                    if is_speaking:
                        silence_counter += 1
                        speech_buffer.append(data)
                        
                        if silence_counter > self._silence_frames_threshold:
                            if speech_frame_count > self._min_speech_frames:
                                is_speaking = False
                                logger.debug("🔇 Speech ended")
                                
                                if speech_buffer:
                                    self._process_speech_segment(speech_buffer)
                            else:
                                logger.debug("🔇 Speech too short, ignoring")
                            
                            speech_buffer = []
                            silence_counter = 0
                            speech_frame_count = 0
                    else:
                        if len(speech_buffer) > 0:
                            speech_buffer = []
                        silence_counter = 0
                
            except Exception as e:
                logger.error(f"VAD streaming error: {e}")
                time.sleep(0.01)
        
        logger.info("🛑 VAD streaming loop stopped")

    def _process_speech_segment(self, speech_buffer: List[bytes]):
        """Process a complete speech segment with transcription."""
        if not speech_buffer:
            return
        
        try:
            audio_data = b''.join(speech_buffer)
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Apply noise reduction to the full segment
            if NOISE_REDUCE_AVAILABLE and self._noise_profile is not None:
                audio_array = self._apply_noise_reduction(audio_array)
            
            text = self._transcribe_audio(audio_array)
            
            if text and text.strip():
                logger.info(f"📝 Streaming transcription: {text}")
                if self._transcription_callback:
                    self._transcription_callback(text)
                
        except Exception as e:
            logger.error(f"Speech processing error: {e}")

    def _transcribe_audio(self, audio_array: np.ndarray) -> Optional[str]:
        """Transcribe audio using Groq API or Whisper fallback."""
        if self.groq_api_key and HAS_REQUESTS:
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    tmp_path = f.name
                
                with wave.open(tmp_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self._sample_rate)
                    wf.writeframes((audio_array * 32768).astype(np.int16).tobytes())
                
                with open(tmp_path, "rb") as f:
                    response = requests.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.groq_api_key}"},
                        files={"file": ("audio.wav", f, "audio/wav")},
                        data={"model": "whisper-large-v3", "language": "en", "response_format": "text"},
                        timeout=10
                    )
                
                os.remove(tmp_path)
                
                if response.status_code == 200 and response.text.strip():
                    return response.text.strip()
                else:
                    logger.warning(f"Groq API error: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Groq transcription failed: {e}")
        
        if self._whisper_model:
            try:
                result = self._whisper_model.transcribe(
                    audio_array,
                    language="en",
                    fp16=False
                )
                return result.get("text", "").strip()
            except Exception as e:
                logger.warning(f"Whisper transcription failed: {e}")
        
        return None

    def stop_streaming(self):
        """Stop continuous streaming."""
        if not self._streaming:
            return
        
        self._stop_streaming = True
        self._streaming = False
        
        if hasattr(self, '_stream'):
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
        
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=2.0)
        
        logger.info("🛑 Streaming stopped")

    def is_streaming(self) -> bool:
        return self._streaming

    def set_vad_threshold(self, threshold: float) -> bool:
        if 0.001 <= threshold <= 0.1:
            self._vad_threshold = threshold
            logger.info(f"VAD threshold set to {threshold:.4f}")
            return True
        return False

    def collect_noise_profile(self) -> Dict[str, Any]:
        """Manually collect noise profile."""
        self._noise_profile_collected = False
        self._collect_noise_profile()
        return {
            "success": self._noise_profile_collected,
            "message": "Noise profile collected" if self._noise_profile_collected else "Failed to collect noise profile",
            "noise_floor": self._noise_floor,
            "vad_threshold": self._vad_threshold
        }

    # =================================================
    # LEGACY METHODS
    # =================================================

    def _speak_sapi(self, text: str) -> bool:
        if not self._sapi_initialized or not self.sapi_speaker:
            return False
        
        if self._is_recording:
            return True
        
        try:
            try:
                pythoncom.CoInitialize()
            except:
                pass
            
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            
            voices = speaker.GetVoices()
            for voice in voices:
                voice_name = voice.GetDescription()
                if "Zira" in voice_name or "David" in voice_name:
                    speaker.Voice = voice
                    break
            
            speaker.Rate = 0
            speaker.Volume = 100
            
            # Set speaking flag to prevent echo
            self._is_speaking_flag = True
            speaker.Speak(text)
            self._is_speaking_flag = False
            return True
        except Exception as e:
            self._is_speaking_flag = False
            logger.error(f"SAPI speak error: {e}")
            return False

    def _speak_fallback(self, text: str) -> bool:
        if not self.fallback_tts:
            return False
        
        if self._is_recording:
            return True
        
        try:
            self._is_speaking_flag = True
            self.fallback_tts.say(text)
            self.fallback_tts.runAndWait()
            self._is_speaking_flag = False
            return True
        except Exception as e:
            self._is_speaking_flag = False
            logger.error(f"Fallback TTS error: {e}")
            return False

    def _speak_sync(self, text: str) -> bool:
        if not text:
            return False
        
        with self._tts_lock:
            if self._sapi_initialized:
                success = self._speak_sapi(text)
                if success:
                    return True
            
            if HAS_TTS and self.fallback_tts:
                return self._speak_fallback(text)
            
            logger.error("No TTS engine available")
            return False

    def _record_audio(self, duration: int = 5) -> Optional[str]:
        if not HAS_PYAUDIO or self.mic_device_index is None:
            logger.error("PyAudio not available or no microphone")
            return None
        
        if self.p is None:
            logger.error("PyAudio not initialized")
            return None
        
        try:
            self._is_recording = True
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            logger.debug(f"Recording from {self.mic_device_name} (index: {self.mic_device_index})")
            
            stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self.mic_device_index,
                frames_per_buffer=CHUNK
            )
            
            frames = []
            for _ in range(int(RATE / CHUNK * duration)):
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                except Exception as e:
                    logger.debug(f"Read error: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            self._is_recording = False

            if not frames:
                logger.warning("No audio data recorded")
                return None

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            
            logger.debug(f"Audio saved to {tmp_path} ({len(frames)} frames)")
            return tmp_path
            
        except Exception as e:
            self._is_recording = False
            logger.error(f"Recording error: {e}")
            return None

    def _transcribe_groq(self, audio_path: str) -> Optional[str]:
        if not self.groq_api_key or not HAS_REQUESTS:
            logger.error("Groq API key not found or requests not available")
            return None
        
        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.groq_api_key}"},
                    files={"file": ("audio.wav", f, "audio/wav")},
                    data={"model": "whisper-large-v3", "language": "en", "response_format": "text"},
                    timeout=30
                )
            
            if response.status_code == 200 and response.text.strip():
                text = response.text.strip()
                logger.info(f"Transcription: {text[:50]}...")
                return text
            else:
                logger.error(f"Transcription error: {response.status_code} - {response.text[:100]}")
                return None
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None

    def _listen_sync(self, duration: int = 5) -> Optional[str]:
        logger.info(f"🎤 Listening for {duration} seconds...")
        
        audio_path = self._record_audio(duration)
        if not audio_path:
            logger.warning("No audio recorded")
            return None
        
        try:
            text = self._transcribe_groq(audio_path)
            return text
        finally:
            try:
                os.remove(audio_path)
            except:
                pass

    def _list_devices_sync(self) -> Dict[str, Any]:
        devices = []
        if not HAS_PYAUDIO or self.p is None:
            return {"success": False, "error": "PyAudio not available"}
        
        try:
            device_count = self.p.get_device_count()
            for i in range(device_count):
                info = self.p.get_device_info_by_index(i)
                is_input = info.get('maxInputChannels', 0) > 0
                devices.append({
                    "index": i,
                    "name": info.get('name', f'Device {i}'),
                    "max_input_channels": info.get('maxInputChannels', 0),
                    "max_output_channels": info.get('maxOutputChannels', 0),
                    "default_sample_rate": info.get('defaultSampleRate', 0),
                    "is_input": is_input
                })
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices),
                "selected": self.mic_device_index,
                "selected_name": self.mic_device_name
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _test_mic_sync(self) -> Dict[str, Any]:
        if self.mic_device_index is None:
            return {"success": False, "error": "No microphone selected"}
        
        try:
            audio_path = self._record_audio(3)
            if not audio_path:
                return {"success": False, "error": "No audio recorded"}
            
            file_size = os.path.getsize(audio_path)
            os.remove(audio_path)
            
            if file_size > 1000:
                return {
                    "success": True,
                    "message": f"Microphone working! Recorded {file_size} bytes",
                    "device": self.mic_device_name,
                    "index": self.mic_device_index
                }
            else:
                return {
                    "success": False,
                    "error": "Audio file too small, microphone may not be working",
                    "bytes": file_size
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "speak":
            text = params.get("text", "")
            if not text:
                return {"success": False, "error": "No text"}
            logger.info(f"🗣️ Speaking: {text[:50]}...")
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._speak_sync, text)
            return {"success": success, "text": text}

        if action == "listen":
            duration = int(params.get("duration", 5))
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._listen_sync, duration)
            if text:
                logger.info(f"📝 Recognized: {text}")
            else:
                logger.info("No speech detected")
            return {
                "success": text is not None,
                "text": text,
                "heard": text is not None
            }

        if action == "list_devices":
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._list_devices_sync)

        if action == "test_mic":
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._test_mic_sync)

        if action == "start_streaming":
            callback = params.get("callback")
            vad_enabled = params.get("vad_enabled", True)
            if not callback:
                return {"success": False, "error": "No callback provided"}
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self.start_streaming, callback, vad_enabled)
            return {"success": success, "message": "Streaming started" if success else "Failed to start streaming"}

        if action == "stop_streaming":
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.stop_streaming)
            return {"success": True, "message": "Streaming stopped"}

        if action == "is_streaming":
            return {"success": True, "streaming": self._streaming}

        if action == "set_vad_threshold":
            threshold = params.get("threshold", 0.035)
            success = self.set_vad_threshold(threshold)
            return {"success": success, "threshold": threshold if success else None}

        if action == "collect_noise_profile":
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.collect_noise_profile)
            return result

        return {"success": False, "error": f"Unknown action: {action}"}