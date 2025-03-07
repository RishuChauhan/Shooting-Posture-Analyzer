#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Detector Module

This module handles audio input and detection for capturing
shooting posture when a gunshot is detected.

Author: Claude
Date: March 6, 2025
"""

import numpy as np
import pyaudio
import time
import threading
import queue
import logging
from typing import Callable, Optional

# Initialize logger
logger = logging.getLogger(__name__)

class AudioDetector:
    """
    Handles audio input and detection for capturing shooting posture.
    Listens for sounds that may indicate a shot was fired.
    """
    
    def __init__(self, 
                 threshold: float = 0.5, 
                 sample_rate: int = 44100, 
                 chunk_size: int = 1024):
        """
        Initialize the audio detector.
        
        Args:
            threshold: Amplitude threshold for detection (0.0-1.0)
            sample_rate: Audio sample rate
            chunk_size: Size of audio chunks to process
        """
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        
        # Audio input setup
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Processing state
        self.is_running = False
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.processor_thread = None
        
        # Callback function to call when shot detected
        self.detection_callback = None
        
        # Cooldown to prevent multiple detections
        self.last_detection_time = 0
        self.detection_cooldown = 1.0  # 1 second cooldown
        
        logger.info("AudioDetector initialized")
    
    def start(self):
        """Start the audio detector."""
        if self.is_running:
            return
        
        try:
            # Open audio stream
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            # Start processing thread
            self.is_running = True
            self.processor_thread = threading.Thread(target=self._processor_loop)
            self.processor_thread.daemon = True
            self.processor_thread.start()
            
            logger.info("AudioDetector started")
            
        except Exception as e:
            logger.error(f"Error starting audio detector: {str(e)}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the audio detector."""
        self.is_running = False
        self.is_listening = False
        
        # Stop processor thread
        if self.processor_thread and self.processor_thread.is_alive():
            self.processor_thread.join(timeout=1.0)
        
        # Stop stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {str(e)}")
            
            self.stream = None
        
        # Clear queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("AudioDetector stopped")
    
    def start_listening(self):
        """Start listening for shots."""
        self.is_listening = True
        logger.info("AudioDetector listening")
    
    def stop_listening(self):
        """Stop listening for shots."""
        self.is_listening = False
        logger.info("AudioDetector stopped listening")
    
    def set_detection_callback(self, callback: Callable):
        """
        Set the callback function to call when a shot is detected.
        
        Args:
            callback: Function to call when shot is detected
        """
        self.detection_callback = callback
    
    def set_threshold(self, threshold: float):
        """
        Set the detection threshold.
        
        Args:
            threshold: Amplitude threshold (0.0-1.0)
        """
        self.threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Detection threshold set to {self.threshold}")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback function for audio stream.
        
        Args:
            in_data: Input audio data
            frame_count: Number of frames
            time_info: Time information
            status: Status flag
            
        Returns:
            Tuple of (None, flag) to continue stream
        """
        if self.is_running and self.is_listening:
            # Queue the audio data for processing
            self.audio_queue.put(in_data)
        
        return (None, pyaudio.paContinue)
    
    def _processor_loop(self):
        """Processing loop that runs in a separate thread."""
        while self.is_running:
            try:
                # Get audio data from queue with timeout
                try:
                    audio_data = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Process audio data
                self._process_audio(audio_data)
                
            except Exception as e:
                logger.error(f"Error in audio processor loop: {str(e)}")
    
    def _process_audio(self, audio_data):
        """
        Process audio data and detect shots.
        
        Args:
            audio_data: Raw audio data
        """
        # Convert byte data to numpy array
        data = np.frombuffer(audio_data, dtype=np.float32)
        
        # Calculate amplitude
        amplitude = np.max(np.abs(data))
        
        # Calculate spectral characteristics of gunshot
        # This is a simplified algorithm - in a real implementation,
        # you would use more sophisticated techniques like FFT analysis
        # to identify the unique spectral signature of a gunshot
        
        # Check if amplitude exceeds threshold (possible shot)
        if amplitude > self.threshold:
            # Check cooldown
            current_time = time.time()
            if current_time - self.last_detection_time >= self.detection_cooldown:
                self._handle_detection(amplitude)
                self.last_detection_time = current_time
    
    def _handle_detection(self, amplitude):
        """
        Handle shot detection.
        
        Args:
            amplitude: Detected amplitude
        """
        logger.info(f"Shot detected with amplitude: {amplitude:.2f}")
        
        # Call the callback function if available
        if self.detection_callback:
            try:
                self.detection_callback()
            except Exception as e:
                logger.error(f"Error in detection callback: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.stop()
        
        # Terminate PyAudio
        if hasattr(self, 'audio') and self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {str(e)}")