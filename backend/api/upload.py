"""File upload API endpoints."""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import shutil
from pathlib import Path
import uuid
from datetime import datetime
import logging

from ..database import get_db
from ..models.database import Document, Chunk, ImageEmbedding, AudioSegment, VectorMetadata, ModalityType
from ..services import (
    get_document_processor,
    get_image_processor,
    get_audio_processor,
    get_embedding_service,
    get_vector_store_manager,
    get_minio_storage
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])

# Temporary upload directory
UPLOAD_DIR = Path("./temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def process_document_background(
    file_path: str,
    document_id: int,
    file_type: str
):
    """Background task to process uploaded document."""
    from ..database import get_db_context
    
    try:
        with get_db_context() as db:
            # Update status to processing
            doc = db.query(Document).filter(Document.id == document_id).first()
            doc.processed = 1  # Processing
            db.commit()
            
            # Get services
            doc_processor = get_document_processor()
            embedding_service = get_embedding_service()
            vector_store_manager = get_vector_store_manager(
                text_dim=embedding_service.get_embedding_dimension("text"),
                image_dim=embedding_service.get_embedding_dimension("image")
            )
            
            # Process document
            chunks, metadata = doc_processor.process_document(file_path, file_type)
            
            # Update document metadata
            doc.metadata = metadata
            db.commit()
            
            # Save chunks and generate embeddings
            chunk_ids = []
            chunk_contents = []
            
            for idx, chunk_data in enumerate(chunks):
                chunk = Chunk(
                    document_id=document_id,
                    content=chunk_data["content"],
                    chunk_index=idx,
                    token_count=chunk_data["token_count"],
                    page_number=chunk_data.get("page_number"),
                    metadata=chunk_data.get("metadata", {})
                )
                db.add(chunk)
                db.flush()
                
                chunk_ids.append(chunk.id)
                chunk_contents.append(chunk_data["content"])
            
            db.commit()
            
            # Generate embeddings
            embeddings = embedding_service.embed_text(chunk_contents)
            
            # Add to vector store
            vector_store_manager.get_store("text").add_embeddings(embeddings, chunk_ids)
            
            # Save vector metadata
            for faiss_idx, chunk_id in enumerate(chunk_ids):
                vm = VectorMetadata(
                    faiss_index=faiss_idx,
                    record_id=chunk_id,
                    modality=ModalityType.TEXT
                )
                db.add(vm)
            
            db.commit()
            
            # Update status to completed
            doc.processed = 2  # Completed
            db.commit()
            
            logger.info(f"Successfully processed document {document_id}")
            
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        with get_db_context() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.processed = 3  # Failed
                db.commit()


def process_image_background(file_path: str, document_id: int):
    """Background task to process uploaded image."""
    from ..database import get_db_context
    
    try:
        with get_db_context() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            doc.processed = 1
            db.commit()
            
            # Get services
            img_processor = get_image_processor()
            embedding_service = get_embedding_service()
            vector_store_manager = get_vector_store_manager(
                text_dim=embedding_service.get_embedding_dimension("text"),
                image_dim=embedding_service.get_embedding_dimension("image")
            )
            
            # Process image
            image, metadata = img_processor.process_image(file_path)
            
            # Update document metadata
            doc.metadata = metadata
            db.commit()
            
            # Save image embedding record
            img_embedding = ImageEmbedding(
                document_id=document_id,
                image_path=doc.minio_path,
                width=metadata["width"],
                height=metadata["height"],
                format=metadata["format"],
                metadata=metadata
            )
            db.add(img_embedding)
            db.flush()
            db.commit()
            
            # Generate embedding
            embedding = embedding_service.embed_image(image)
            
            # Add to vector store
            vector_store_manager.get_store("image").add_embeddings(embedding, [img_embedding.id])
            
            # Save vector metadata
            vm = VectorMetadata(
                faiss_index=0,
                record_id=img_embedding.id,
                modality=ModalityType.IMAGE
            )
            db.add(vm)
            db.commit()
            
            doc.processed = 2
            db.commit()
            
            logger.info(f"Successfully processed image {document_id}")
            
    except Exception as e:
        logger.error(f"Error processing image {document_id}: {e}")
        with get_db_context() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.processed = 3
                db.commit()


def process_audio_background(file_path: str, document_id: int):
    """Background task to process uploaded audio."""
    from ..database import get_db_context
    
    try:
        with get_db_context() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            doc.processed = 1
            db.commit()
            
            # Get services
            audio_processor = get_audio_processor()
            embedding_service = get_embedding_service()
            vector_store_manager = get_vector_store_manager(
                text_dim=embedding_service.get_embedding_dimension("text"),
                image_dim=embedding_service.get_embedding_dimension("image")
            )
            
            # Process audio
            segments, metadata = audio_processor.transcribe_audio(file_path)
            
            # Merge short segments
            segments = audio_processor.merge_short_segments(segments)
            
            # Update document metadata
            doc.metadata = metadata
            db.commit()
            
            # Save segments and generate embeddings
            segment_ids = []
            transcripts = []
            
            for segment_data in segments:
                segment = AudioSegment(
                    document_id=document_id,
                    transcript=segment_data["transcript"],
                    start_time=segment_data["start_time"],
                    end_time=segment_data["end_time"],
                    confidence=segment_data.get("confidence", 0.0),
                    metadata={"words": segment_data.get("words", [])}
                )
                db.add(segment)
                db.flush()
                
                segment_ids.append(segment.id)
                transcripts.append(segment_data["transcript"])
            
            db.commit()
            
            # Generate embeddings from transcripts
            embeddings = embedding_service.embed_text(transcripts)
            
            # Add to vector store
            vector_store_manager.get_store("audio").add_embeddings(embeddings, segment_ids)
            
            # Save vector metadata
            for faiss_idx, segment_id in enumerate(segment_ids):
                vm = VectorMetadata(
                    faiss_index=faiss_idx,
                    record_id=segment_id,
                    modality=ModalityType.AUDIO
                )
                db.add(vm)
            
            db.commit()
            
            doc.processed = 2
            db.commit()
            
            logger.info(f"Successfully processed audio {document_id}")
            
    except Exception as e:
        logger.error(f"Error processing audio {document_id}: {e}")
        with get_db_context() as db:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.processed = 3
                db.commit()


@router.post("/document")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload PDF or DOCX document."""
    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")
    
    try:
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = UPLOAD_DIR / unique_filename
        
        # Save uploaded file
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Upload to MinIO
        minio_storage = get_minio_storage()
        minio_path = f"documents/{unique_filename}"
        minio_storage.upload_file(str(temp_path), minio_path)
        
        # Create database record
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_type=file_ext[1:],  # Remove dot
            modality=ModalityType.TEXT,
            file_size=temp_path.stat().st_size,
            minio_path=minio_path,
            processed=0
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Process in background
        background_tasks.add_task(
            process_document_background,
            str(temp_path),
            document.id,
            file_ext[1:]
        )
        
        return {
            "message": "Document uploaded successfully",
            "document_id": document.id,
            "filename": file.filename,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image")
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload image file."""
    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
        raise HTTPException(status_code=400, detail="Only image files are supported")
    
    try:
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = UPLOAD_DIR / unique_filename
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        minio_storage = get_minio_storage()
        minio_path = f"images/{unique_filename}"
        minio_storage.upload_file(str(temp_path), minio_path)
        
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_type=file_ext[1:],
            modality=ModalityType.IMAGE,
            file_size=temp_path.stat().st_size,
            minio_path=minio_path,
            processed=0
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        background_tasks.add_task(process_image_background, str(temp_path), document.id)
        
        return {
            "message": "Image uploaded successfully",
            "document_id": document.id,
            "filename": file.filename,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload audio file."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".mp3", ".wav", ".m4a", ".flac", ".ogg"]:
        raise HTTPException(status_code=400, detail="Only audio files are supported")
    
    try:
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = UPLOAD_DIR / unique_filename
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        minio_storage = get_minio_storage()
        minio_path = f"audio/{unique_filename}"
        minio_storage.upload_file(str(temp_path), minio_path)
        
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_type=file_ext[1:],
            modality=ModalityType.AUDIO,
            file_size=temp_path.stat().st_size,
            minio_path=minio_path,
            processed=0
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        background_tasks.add_task(process_audio_background, str(temp_path), document.id)
        
        return {
            "message": "Audio uploaded successfully",
            "document_id": document.id,
            "filename": file.filename,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
