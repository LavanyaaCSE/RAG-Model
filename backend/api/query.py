"""Query API endpoint for RAG."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging

from ..database import get_db
from ..models.database import Document, Chunk, ImageEmbedding, AudioSegment
from ..services import (
    get_embedding_service,
    get_vector_store_manager,
    get_rag_engine,
    get_minio_storage
)
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/query", tags=["query"])
settings = get_settings()


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    include_modalities: List[str] = ["text", "image", "audio"]


class Citation(BaseModel):
    id: int
    type: str
    source: str
    page: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    url: Optional[str] = None
    chunk_id: Optional[int] = None
    image_id: Optional[int] = None
    segment_id: Optional[int] = None
    document_id: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    context_used: Dict[str, int]


@router.post("/", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Answer question using RAG."""
    try:
        embedding_service = get_embedding_service()
        vector_store_manager = get_vector_store_manager(
            text_dim=embedding_service.get_embedding_dimension("text"),
            image_dim=embedding_service.get_embedding_dimension("image")
        )
        rag_engine = get_rag_engine()
        minio_storage = get_minio_storage()
        
        # Retrieve relevant context from each modality
        context_chunks = []
        context_images = []
        context_audio = []
        
        # Text chunks
        if "text" in request.include_modalities:
            text_embedding = embedding_service.embed_text(request.question)
            text_ids, text_scores = vector_store_manager.get_store("text").search(
                text_embedding,
                k=request.top_k
            )
            
            for chunk_id, score in zip(text_ids, text_scores):
                chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()
                if chunk:
                    doc = db.query(Document).filter(Document.id == chunk.document_id).first()
                    context_chunks.append({
                        "content": chunk.content,
                        "filename": doc.original_filename if doc else "Unknown",
                        "page_number": chunk.page_number,
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "score": score
                    })
        
        # Images
        if "image" in request.include_modalities:
            image_embedding = embedding_service.embed_text_for_image_search(request.question)
            image_ids, image_scores = vector_store_manager.get_store("image").search(
                image_embedding,
                k=request.top_k
            )
            
            for img_id, score in zip(image_ids, image_scores):
                img = db.query(ImageEmbedding).filter(ImageEmbedding.id == img_id).first()
                if img:
                    doc = db.query(Document).filter(Document.id == img.document_id).first()
                    url = minio_storage.get_file_url(img.image_path)
                    context_images.append({
                        "filename": doc.original_filename if doc else "Unknown",
                        "caption": img.caption,
                        "image_id": img.id,
                        "document_id": img.document_id,
                        "url": url,
                        "score": score
                    })
        
        # Audio
        if "audio" in request.include_modalities:
            audio_embedding = embedding_service.embed_text(request.question)
            audio_ids, audio_scores = vector_store_manager.get_store("audio").search(
                audio_embedding,
                k=request.top_k
            )
            
            for seg_id, score in zip(audio_ids, audio_scores):
                segment = db.query(AudioSegment).filter(AudioSegment.id == seg_id).first()
                if segment:
                    doc = db.query(Document).filter(Document.id == segment.document_id).first()
                    context_audio.append({
                        "transcript": segment.transcript,
                        "filename": doc.original_filename if doc else "Unknown",
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "segment_id": segment.id,
                        "document_id": segment.document_id,
                        "score": score
                    })
        
        # Generate answer with RAG
        result = rag_engine.generate_answer(
            query=request.question,
            context_chunks=context_chunks,
            context_images=context_images,
            context_audio=context_audio
        )
        
        # Convert citations to response format
        citations = [Citation(**citation) for citation in result["citations"]]
        
        return QueryResponse(
            answer=result["answer"],
            citations=citations,
            context_used=result["context_used"]
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
