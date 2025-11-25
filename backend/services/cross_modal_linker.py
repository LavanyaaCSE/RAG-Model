"""Cross-modal linking service."""
from typing import List, Dict
import numpy as np
from sqlalchemy.orm import Session
from ..models.database import Document, Chunk, ImageEmbedding, AudioSegment
import logging

logger = logging.getLogger(__name__)


class CrossModalLinker:
    """Link related content across different modalities."""
    
    def find_related_content(
        self,
        db: Session,
        source_id: int,
        source_type: str,
        similarity_threshold: float = 0.7
    ) -> Dict[str, List[Dict]]:
        """
        Find content related to a source across modalities.
        
        Args:
            db: Database session
            source_id: ID of source (chunk_id, image_id, or segment_id)
            source_type: Type of source ("text", "image", or "audio")
            similarity_threshold: Minimum similarity score
            
        Returns:
            Dictionary with related content by modality
        """
        related = {
            "text": [],
            "images": [],
            "audio": []
        }
        
        # Get source document
        if source_type == "text":
            source = db.query(Chunk).filter(Chunk.id == source_id).first()
            if not source:
                return related
            document_id = source.document_id
            
        elif source_type == "image":
            source = db.query(ImageEmbedding).filter(ImageEmbedding.id == source_id).first()
            if not source:
                return related
            document_id = source.document_id
            
        elif source_type == "audio":
            source = db.query(AudioSegment).filter(AudioSegment.id == source_id).first()
            if not source:
                return related
            document_id = source.document_id
        else:
            return related
        
        # Find content from same document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return related
        
        # Get related text chunks
        if source_type != "text":
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
            related["text"] = [{
                "chunk_id": chunk.id,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "document_id": chunk.document_id
            } for chunk in chunks]
        
        # Get related images
        if source_type != "image":
            images = db.query(ImageEmbedding).filter(ImageEmbedding.document_id == document_id).all()
            related["images"] = [{
                "image_id": img.id,
                "path": img.image_path,
                "caption": img.caption,
                "document_id": img.document_id
            } for img in images]
        
        # Get related audio segments
        if source_type != "audio":
            segments = db.query(AudioSegment).filter(AudioSegment.document_id == document_id).all()
            related["audio"] = [{
                "segment_id": seg.id,
                "transcript": seg.transcript,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "document_id": seg.document_id
            } for seg in segments]
        
        return related
    
    def link_by_timestamp(
        self,
        db: Session,
        audio_segment_id: int,
        time_window: float = 30.0
    ) -> List[Dict]:
        """
        Find content related by timestamp (e.g., slides shown during audio).
        
        Args:
            db: Database session
            audio_segment_id: Audio segment ID
            time_window: Time window in seconds
            
        Returns:
            List of related content with timestamps
        """
        segment = db.query(AudioSegment).filter(AudioSegment.id == audio_segment_id).first()
        if not segment:
            return []
        
        # Find other segments in time window
        related_segments = db.query(AudioSegment).filter(
            AudioSegment.document_id == segment.document_id,
            AudioSegment.id != audio_segment_id,
            AudioSegment.start_time >= segment.start_time - time_window,
            AudioSegment.end_time <= segment.end_time + time_window
        ).all()
        
        return [{
            "segment_id": seg.id,
            "transcript": seg.transcript,
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "time_offset": abs(seg.start_time - segment.start_time)
        } for seg in related_segments]


# Global instance
_cross_modal_linker = None


def get_cross_modal_linker() -> CrossModalLinker:
    """Get singleton cross-modal linker instance."""
    global _cross_modal_linker
    if _cross_modal_linker is None:
        _cross_modal_linker = CrossModalLinker()
    return _cross_modal_linker
