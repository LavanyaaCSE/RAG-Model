"""Document management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging

from ..database import get_db
from ..models.database import Document, Chunk, ImageEmbedding, AudioSegment, ModalityType
from ..services import get_minio_storage, get_vector_store_manager, get_embedding_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    modality: str
    file_size: int
    upload_date: str
    processed: int
    metadata: Optional[dict] = None
    url: Optional[str] = None


class ChunkResponse(BaseModel):
    id: int
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    token_count: int


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    modality: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all documents."""
    try:
        query = db.query(Document)
        
        if modality:
            query = query.filter(Document.modality == modality)
        
        documents = query.offset(skip).limit(limit).all()
        
        minio_storage = get_minio_storage()
        
        result = []
        for doc in documents:
            # Get presigned URL
            url = minio_storage.get_file_url(doc.minio_path)
            
            result.append(DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                modality=doc.modality.value,
                file_size=doc.file_size,
                upload_date=doc.upload_date.isoformat(),
                processed=doc.processed,
                metadata=doc.metadata,
                url=url
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get document details."""
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        minio_storage = get_minio_storage()
        url = minio_storage.get_file_url(doc.minio_path)
        
        return DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            modality=doc.modality.value,
            file_size=doc.file_size,
            upload_date=doc.upload_date.isoformat(),
            processed=doc.processed,
            metadata=doc.metadata,
            url=url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get all chunks for a document."""
    try:
        chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
        
        return [ChunkResponse(
            id=chunk.id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            token_count=chunk.token_count
        ) for chunk in chunks]
        
    except Exception as e:
        logger.error(f"Error getting chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Delete a document and all associated data."""
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get embedding service for dimensions
        embedding_service = get_embedding_service()
        vector_store_manager = get_vector_store_manager(
            text_dim=embedding_service.get_embedding_dimension("text"),
            image_dim=embedding_service.get_embedding_dimension("image")
        )
        
        # Delete from vector stores based on modality
        if doc.modality == ModalityType.TEXT:
            chunk_ids = [chunk.id for chunk in doc.chunks]
            if chunk_ids:
                vector_store_manager.get_store("text").delete_by_ids(chunk_ids)
                
        elif doc.modality == ModalityType.IMAGE:
            image_ids = [img.id for img in doc.image_embeddings]
            if image_ids:
                vector_store_manager.get_store("image").delete_by_ids(image_ids)
                
        elif doc.modality == ModalityType.AUDIO:
            segment_ids = [seg.id for seg in doc.audio_segments]
            if segment_ids:
                vector_store_manager.get_store("audio").delete_by_ids(segment_ids)
        
        # Delete from MinIO
        minio_storage = get_minio_storage()
        minio_storage.delete_file(doc.minio_path)
        
        # Delete from database (cascades to chunks, images, audio)
        db.delete(doc)
        db.commit()
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
