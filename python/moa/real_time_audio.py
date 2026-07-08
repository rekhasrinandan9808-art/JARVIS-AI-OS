"""
moa/real_time_audio.py
Real-Time Audio Processing - Continuous streaming with VAD
"""

import os
import time
import queue
import threading
import numpy as np
import sounddevice as sd
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger("jarvis.real_time_audio")

# Try to import Silero VAD
try:
    import torch
    import torchaudio
    from silero_vad import load_silero_vad, get_speech_timestamps
    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False
    logger.warning("Silero VAD not available. Install: pip install silero-vad torch torchaudio")


@dataclass
class AudioChunk:
    """Audio chunk with timestamp."""
    data: bytes
    timestamp: float
    sample_rate: int
    duration: float


class VoiceActivityDetector:
    """
    Voice Activity Detection using Silero VAD.
    """
    
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.is_speaking = False
        self.speech_buffer = []
        self.silence_counter = 0
        self.speech_counter = 0
        self.min_speech_frames = 10  # Minimum frames to consider as speech
        self.max_silence_frames = 20  # Maximum silence frames before speech ends
        
        # Initialize Silero VAD
        self.vad_model = None
        if SILERO_AVAILABLE:
            try:
                self.vad_model = load_silero_vad()
                logger.info("✅ Silero VAD loaded")
            except Exception as e:
                logger.error(f"Silero VAD load error: {e}")
        
        logger.info(f"VAD initialized (rate: {sample_rate}, threshold: {threshold})")
    
    def process_chunk(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Process audio chunk and detect voice activity.
        
        Returns:
            Dict with speech detection status
        """
        # Ensure audio is float32 and normalized
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
        else:
            audio_float = audio_data.astype(np.float32)
        
        # Use Silero VAD if available
        if self.vad_model is not None:
            return self._process_silero(audio_float)
        else:
            return self._process_energy(audio_float)
    
    def _process_silero(self, audio_float: np.ndarray) -> Dict[str, Any]:
        """Process using Silero VAD."""
        try:
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio_float).float()
            
            # Get speech probability
            speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()
            
            was_speaking = self.is_speaking
            
            # Update state based on probability
            if speech_prob > self.threshold:
                self.speech_counter += 1
                self.silence_counter = 0
                if self.speech_counter > self.min_speech_frames:
                    self.is_speaking = True
            else:
                self.silence_counter += 1
                if self.silence_counter > self.max_silence_frames:
                    self.is_speaking = False
                    self.speech_counter = 0
            
            return {
                "speaking": self.is_speaking,
                "probability": speech_prob,
                "speech_started": self.is_speaking and not was_speaking,
                "speech_ended": not self.is_speaking and was_speaking,
                "energy": speech_prob * 100
            }
        except Exception as e:
            logger.debug(f"Silero VAD error: {e}")
            return self._process_energy(audio_float)
    
    def _process_energy(self, audio_float: np.ndarray) -> Dict[str, Any]:
        """Fallback: Energy-based VAD."""
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_float ** 2))
        energy = rms * 10000
        
        # Use energy threshold
        was_speaking = self.is_speaking
        threshold = 0.005  # Adjust based on testing
        
        if energy > threshold:
            self.speech_counter += 1
            self.silence_counter = 0
            if self.speech_counter > self.min_speech_frames:
                self.is_speaking = True
        else:
            self.silence_counter += 1
            if self.silence_counter > self.max_silence_frames:
                self.is_speaking = False
                self.speech_counter = 0
        
        return {
            "speaking": self.is_speaking,
            "probability": energy / 100,
            "speech_started": self.is_speaking and not was_speaking,
            "speech_ended": not self.is_speaking and was_speaking,
            "energy": energy
        }


class RealTimeAudio:
    """
    Real-time audio capture with continuous streaming and VAD.
    """
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024, device_index: int = None):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.stream = None
        self.vad = VoiceActivityDetector(sample_rate)
        self.callbacks = []
        self.speech_buffer = bytearray()
        self.is_speech_active = False
        
        logger.info(f"RealTimeAudio initialized (rate: {sample_rate}, chunk: {chunk_size})")
    
    def register_callback(self, callback: Callable):
        """Register a callback for audio events."""
        self.callbacks.append(callback)
    
    def start(self):
        """Start continuous audio capture."""
        if self.is_recording:
            return
        
        self.is_recording = True
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.debug(f"Audio status: {status}")
            if self.is_recording:
                audio_data = indata.flatten()
                self.audio_queue.put(audio_data)
        
        self.stream = sd.InputStream(
            callback=audio_callback,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            dtype=np.int16,
            device=self.device_index
        )
        self.stream.start()
        
        # Start processing thread
        self.process_thread = threading.Thread(target=self._process_audio, daemon=True)
        self.process_thread.start()
        
        logger.info("🎤 Real-time audio capture started")
    
    def stop(self):
        """Stop audio capture."""
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        logger.info("🛑 Real-time audio capture stopped")
    
    def _process_audio(self):
        """Process audio chunks from the queue with VAD."""
        while self.is_recording:
            try:
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # VAD processing
                vad_result = self.vad.process_chunk(audio_data)
                
                # Handle speech state changes
                if vad_result.get("speech_started"):
                    self.speech_buffer = bytearray()
                    self.is_speech_active = True
                    logger.debug("Speech started")
                    self._notify("speech_start", {"timestamp": time.time()})
                
                elif vad_result.get("speech_ended"):
                    self.is_speech_active = False
                    logger.debug("Speech ended")
                    if len(self.speech_buffer) > 0:
                        # Process the collected speech
                        speech_audio = bytes(self.speech_buffer)
                        self._notify("speech_end", {
                            "audio": speech_audio,
                            "duration": len(speech_audio) / self.sample_rate,
                            "timestamp": time.time()
                        })
                    self.speech_buffer = bytearray()
                
                # Store audio if speaking
                if self.is_speech_active:
                    self.speech_buffer.extend(audio_data.tobytes())
                
                # Notify VAD state
                self._notify("vad_state", vad_result)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Audio processing error: {e}")
    
    def _notify(self, event: str, data: Dict[str, Any]):
        """Notify all callbacks."""
        for callback in self.callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_audio_chunk(self, block: bool = True) -> Optional[AudioChunk]:
        """Get the next audio chunk."""
        try:
            data = self.audio_queue.get(block=block, timeout=0.5)
            return AudioChunk(
                data=data.tobytes(),
                timestamp=time.time(),
                sample_rate=self.sample_rate,
                duration=len(data) / self.sample_rate
            )
        except queue.Empty:
            return None