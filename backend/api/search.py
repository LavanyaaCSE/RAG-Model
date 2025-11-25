"""Search API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging

from ..database import get_db
from ..models.database import Document, Chunk, ImageEmbedding, AudioSegment
from ..services import (
    get_embedding_service,
    get_vector_store_manager,
    get_minio_storage
)
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])
settings = get_settings()


class TextSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    modalities: List[str] = ["text", "image", "audio"]


class SearchResult(BaseModel):
    id: int
    type: str
    content: Optional[str] = None
    filename: str
    score: float
    metadata: dict


@router.post("/text", response_model=List[SearchResult])
async def search_text(
    request: TextSearchRequest,
    db: Session = Depends(get_db)
):
    """Search across all modalities using text query."""
    try:
        embedding_service = get_embedding_service()
        vector_store_manager = get_vector_store_manager(
            text_dim=embedding_service.get_embedding_dimension("text"),
            image_dim=embedding_service.get_embedding_dimension("image")
        )
        minio_storage = get_minio_storage()
        
        results = []
        
        # Search text chunks
        if "text" in request.modalities:
            text_embedding = embedding_service.embed_text(request.query)
            text_ids, text_scores = vector_store_manager.get_store("text").search(
                text_embedding,
                k=request.top_k
            )
            
            for chunk_id, score in zip(text_ids, text_scores):
                chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()
                if chunk:
                    doc = db.query(Document).filter(Document.id == chunk.document_id).first()
                    results.append(SearchResult(
                        id=chunk.id,
                        type="text",
                        content=chunk.content,
                        filename=doc.original_filename if doc else "Unknown",
                        score=float(score),
                        metadata={
                            "page_number": chunk.page_number,
                            "chunk_index": chunk.chunk_index,
                            "document_id": chunk.document_id
                        }
                    ))
        
        # Search images (using CLIP text encoder)
        if "image" in request.modalities:
            image_embedding = embedding_service.embed_text_for_image_search(request.query)
            image_ids, image_scores = vector_store_manager.get_store("image").search(
                image_embedding,
                k=request.top_k
            )
            
            for img_id, score in zip(image_ids, image_scores):
                img = db.query(ImageEmbedding).filter(ImageEmbedding.id == img_id).first()
                if img:
                    doc = db.query(Document).filter(Document.id == img.document_id).first()
                    # Get presigned URL
                    url = minio_storage.get_file_url(img.image_path)
                    results.append(SearchResult(
                        id=img.id,
                        type="image",
                        content=img.caption,
                        filename=doc.original_filename if doc else "Unknown",
                        score=float(score),
                        metadata={
                            "width": img.width,
                            "height": img.height,
                            "url": url,
                            "document_id": img.document_id
                        }
                    ))
        
        # Search audio transcripts
        if "audio" in request.modalities:
            audio_embedding = embedding_service.embed_text(request.query)
            audio_ids, audio_scores = vector_store_manager.get_store("audio").search(
                audio_embedding,
                k=request.top_k
            )
            
            for seg_id, score in zip(audio_ids, audio_scores):
                segment = db.query(AudioSegment).filter(AudioSegment.id == seg_id).first()
                if segment:
                    doc = db.query(Document).filter(Document.id == segment.document_id).first()
                    results.append(SearchResult(
                        id=segment.id,
                        type="audio",
                        content=segment.transcript,
                        filename=doc.original_filename if doc else "Unknown",
                        score=float(score),
                        metadata={
                            "start_time": segment.start_time,
                            "end_time": segment.end_time,
                            "confidence": segment.confidence,
                            "document_id": segment.document_id
                        }
                    ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:request.top_k * len(request.modalities)]
        
    except Exception as e:
        logger.error(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hybrid")
async def hybrid_search(
    request: TextSearchRequest,
    db: Session = Depends(get_db)
):
    """Hybrid search with query expansion."""
    try:
        from ..services import get_rag_engine
        
        rag_engine = get_rag_engine()
        
        # Expand query
        expanded_queries = rag_engine.expand_query(request.query)
        logger.info(f"Expanded queries: {expanded_queries}")
        
        # Search with each expanded query
        all_results = {}
        
        for query in expanded_queries:
            search_request = TextSearchRequest(
                query=query,
                top_k=request.top_k,
                modalities=request.modalities
            )
            results = await search_text(search_request, db)
            
            # Aggregate results
            for result in results:
                key = (result.type, result.id)
                if key in all_results:
                    # Average scores
                    all_results[key].score = (all_results[key].score + result.score) / 2
                else:
                    all_results[key] = result
        
        # Sort and return
        final_results = sorted(all_results.values(), key=lambda x: x.score, reverse=True)
        return final_results[:request.top_k * len(request.modalities)]
        
    except Exception as e:
        logger.error(f"Error in hybrid search: {e}")
        raise HTTPException(status_code=500, detail=str(e))
