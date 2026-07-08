"""
moa/wake_word.py
Wake Word Detection - "Hey JARVIS" using Porcupine
"""

import os
import time
import threading
import logging
from typing import Optional, Callable

logger = logging.getLogger("jarvis.wake_word")


class WakeWordDetector:
    """
    Wake word detection using Porcupine.
    Default wake word: "Hey JARVIS"
    """
    
    def __init__(self, wake_word: str = "hey jarvis", sensitivity: float = 0.5):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self._running = False
        self._thread = None
        self._callback = None
        self._porcupine = None
        self._audio = None
        
        # Try to initialize Porcupine
        self._init_porcupine()
    
    def _init_porcupine(self):
        """Initialize Porcupine wake word detection."""
        try:
            import pvporcupine
            import pyaudio
            
            # Get access key from environment or use default
            access_key = os.getenv("PORCUPINE_ACCESS_KEY", "")
            
            if not access_key:
                logger.warning("PORCUPINE_ACCESS_KEY not set. Wake word disabled.")
                return
            
            # Create Porcupine instance
            self._porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=[self.wake_word],
                sensitivities=[self.sensitivity]
            )
            
            # Initialize audio
            self._audio = pyaudio.PyAudio()
            self._audio_stream = self._audio.open(
                rate=self._porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self._porcupine.frame_length
            )
            
            logger.info(f"✅ Wake word detector initialized: '{self.wake_word}'")
            
        except ImportError:
            logger.warning("⚠️ Porcupine not installed. Wake word disabled.")
            logger.info("Install: pip install pvporcupine pyaudio")
        except Exception as e:
            logger.error(f"❌ Wake word initialization failed: {e}")
    
    def start(self, callback: Callable):
        """Start wake word detection in background."""
        if not self._porcupine:
            logger.warning("Wake word not available")
            return False
        
        if self._running:
            return True
        
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        
        logger.info("🎤 Wake word detection started - Say 'Hey JARVIS'")
        return True
    
    def _listen_loop(self):
        """Background listening loop."""
        while self._running:
            try:
                # Read audio
                pcm = self._audio_stream.read(self._porcupine.frame_length)
                pcm = [int.from_bytes(pcm[i:i+2], "little") for i in range(0, len(pcm), 2)]
                
                # Check for wake word
                keyword_index = self._porcupine.process(pcm)
                
                if keyword_index >= 0:
                    logger.info(f"🔊 Wake word detected: '{self.wake_word}'")
                    if self._callback:
                        self._callback()
                    
                    # Cooldown to avoid multiple triggers
                    time.sleep(1)
                    
            except Exception as e:
                logger.debug(f"Wake word error: {e}")
                time.sleep(0.1)
    
    def stop(self):
        """Stop wake word detection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._audio_stream:
            self._audio_stream.stop_stream()
            self._audio_stream.close()
        if self._audio:
            self._audio.terminate()
        logger.info("🛑 Wake word detection stopped")
    
    def is_available(self) -> bool:
        """Check if wake word detection is available."""
        return self._porcupine is not None