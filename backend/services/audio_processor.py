"""Audio processing service using Whisper."""
import whisper
import numpy as np
from typing import List, Dict
import logging
from pathlib import Path
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AudioProcessor:
    """Process audio files and transcribe using Whisper."""
    
    def __init__(self):
        """Initialize Whisper model."""
        # Extract model size from config (e.g., "openai/whisper-medium" -> "medium")
        model_size = settings.audio_model.split("-")[-1] if "-" in settings.audio_model else "medium"
        
        logger.info(f"Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        
    def transcribe_audio(self, file_path: str) -> Tuple[List[Dict], Dict]:
        """
        Transcribe audio file and return segments with timestamps.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (segments, metadata)
        """
        try:
            logger.info(f"Transcribing audio file: {file_path}")
            
            # Transcribe with word-level timestamps
            result = self.model.transcribe(
                file_path,
                word_timestamps=True,
                verbose=False
            )
            
            # Extract segments
            segments = []
            for segment in result["segments"]:
                segments.append({
                    "transcript": segment["text"].strip(),
                    "start_time": segment["start"],
                    "end_time": segment["end"],
                    "confidence": segment.get("confidence", 0.0),
                    "words": segment.get("words", [])
                })
            
            # Metadata
            metadata = {
                "language": result.get("language", "unknown"),
                "duration": result.get("duration", 0.0),
                "segments_count": len(segments)
            }
            
            logger.info(f"Transcription complete: {len(segments)} segments, language: {metadata['language']}")
            
            return segments, metadata
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    def merge_short_segments(self, segments: List[Dict], min_duration: float = 5.0) -> List[Dict]:
        """
        Merge short segments to create more coherent chunks.
        
        Args:
            segments: List of segment dictionaries
            min_duration: Minimum duration for merged segments
            
        Returns:
            List of merged segments
        """
        if not segments:
            return []
        
        merged = []
        current_segment = segments[0].copy()
        
        for segment in segments[1:]:
            current_duration = current_segment["end_time"] - current_segment["start_time"]
            
            if current_duration < min_duration:
                # Merge with current
                current_segment["transcript"] += " " + segment["transcript"]
                current_segment["end_time"] = segment["end_time"]
                if "words" in current_segment and "words" in segment:
                    current_segment["words"].extend(segment["words"])
            else:
                # Save current and start new
                merged.append(current_segment)
                current_segment = segment.copy()
        
        # Add last segment
        merged.append(current_segment)
        
        return merged


# Global instance
_audio_processor = None


def get_audio_processor() -> AudioProcessor:
    """Get singleton audio processor instance."""
    global _audio_processor
    if _audio_processor is None:
        _audio_processor = AudioProcessor()
    return _audio_processor
