"""Database models for the multimodal RAG system."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import enum


class Base(DeclarativeBase):
    pass


class ModalityType(str, enum.Enum):
    """Supported modality types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"


class Document(Base):
    """Document metadata table."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, png, jpg, mp3, wav
    modality = Column(String(20), nullable=False)  # text, image, audio
    file_size = Column(Integer)  # bytes
    minio_path = Column(String(512), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)  # 0=pending, 1=processing, 2=completed, 3=failed
    metadata = Column(JSON)  # Additional metadata (pages, duration, dimensions, etc.)
    
    # Relationships
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    image_embeddings = relationship("ImageEmbedding", back_populates="document", cascade="all, delete-orphan")
    audio_segments = relationship("AudioSegment", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """Text chunks with embeddings."""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    token_count = Column(Integer)
    page_number = Column(Integer)  # For PDFs
    metadata = Column(JSON)  # Additional context (section, heading, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")


class ImageEmbedding(Base):
    """Image embeddings and metadata."""
    __tablename__ = "image_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    image_path = Column(String(512), nullable=False)  # MinIO path
    width = Column(Integer)
    height = Column(Integer)
    format = Column(String(20))
    caption = Column(Text)  # Optional user-provided or generated caption
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="image_embeddings")


class AudioSegment(Base):
    """Audio transcripts with timestamps."""
    __tablename__ = "audio_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    transcript = Column(Text, nullable=False)
    start_time = Column(Float)  # seconds
    end_time = Column(Float)  # seconds
    confidence = Column(Float)  # Whisper confidence score
    speaker = Column(String(100))  # Optional speaker identification
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="audio_segments")


class VectorMetadata(Base):
    """Mapping between FAISS indices and database records."""
    __tablename__ = "vector_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    faiss_index = Column(Integer, nullable=False)  # Position in FAISS index
    record_id = Column(Integer, nullable=False)  # ID in chunks/image_embeddings/audio_segments
    modality = Column(String(20), nullable=False)  # text, image, audio
    created_at = Column(DateTime, default=datetime.utcnow)
