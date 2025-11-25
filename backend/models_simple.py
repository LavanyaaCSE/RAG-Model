"""Simplified database models - SQLAlchemy 2.0 compatible."""
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import Optional


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Document(Base):
    """Document metadata table."""
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column()
    original_filename: Mapped[str] = mapped_column()
    file_type: Mapped[str] = mapped_column()
    modality: Mapped[str] = mapped_column()  # text, image, audio
    file_size: Mapped[Optional[int]] = mapped_column(default=None)
    minio_path: Mapped[str] = mapped_column()
    upload_date: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    processed: Mapped[int] = mapped_column(default=0)  # 0=pending, 1=processing, 2=completed, 3=failed
    metadata: Mapped[Optional[dict]] = mapped_column(default=None)
