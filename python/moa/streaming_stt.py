"""
moa/streaming_stt.py
Streaming Speech-to-Text using Faster-Whisper
"""

import os
import time
import threading
import queue
import tempfile
import wave
import numpy as np
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger("jarvis.streaming_stt")


@dataclass
class TranscriptionResult:
    """Transcription result with metadata."""
    text: str
    is_final: bool
    timestamp: float
    confidence: float = 0.0


class StreamingSTT:
    """
    Streaming Speech-to-Text using Faster-Whisper.
    Supports continuous transcription with partial results.
    """
    
    def __init__(self, model_size: str = "tiny", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self.model = None
        self.is_initialized = False
        self.transcription_queue = queue.Queue()
        self.callbacks = []
        
        # Audio buffer for streaming
        self.audio_buffer = bytearray()
        self.sample_rate = 16000
        
        self._init_model()
    
    def _init_model(self):
        """Initialize Faster-Whisper model."""
        try:
            from faster_whisper import WhisperModel
            
            logger.info(f"Loading Faster-Whisper model '{self.model_size}' on {self.device}...")
            self.model = WhisperModel(self.model_size, device=self.device)
            self.is_initialized = True
            logger.info("✅ Streaming STT initialized")
        except ImportError:
            logger.warning("faster-whisper not installed. Install: pip install faster-whisper")
        except Exception as e:
            logger.error(f"STT initialization error: {e}")
    
    def register_callback(self, callback: Callable):
        """Register callback for transcriptions."""
        self.callbacks.append(callback)
    
    def process_audio(self, audio_data: bytes, duration: float = 0) -> Optional[TranscriptionResult]:
        """
        Process audio chunk and transcribe.
        """
        if not self.is_initialized or not self.model:
            return None
        
        try:
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio_np,
                beam_size=5,
                language="en",
                vad_filter=False
            )
            
            # Get transcription
            text = " ".join([seg.text for seg in segments])
            
            if text.strip():
                result = TranscriptionResult(
                    text=text,
                    is_final=True,  # For streaming, would be partial
                    timestamp=time.time(),
                    confidence=1.0
                )
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                return result
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
        
        return None
    
    def transcribe_file(self, audio_path: str) -> Optional[str]:
        """Transcribe an audio file."""
        if not self.is_initialized or not self.model:
            return None
        
        try:
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                language="en"
            )
            
            text = " ".join([seg.text for seg in segments])
            return text if text.strip() else None
            
        except Exception as e:
            logger.error(f"File transcription error: {e}")
            return None
    
    def save_audio_to_file(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Save audio data to a WAV file."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data)
            
            return temp_path
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return None