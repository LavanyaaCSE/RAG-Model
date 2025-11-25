"""Configuration management for the multimodal RAG system."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://raguser:ragpassword@localhost:5432/multimodal_rag"
    
    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket_name: str = "rag-documents"
    minio_secure: bool = False
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    
    # Embedding Models
    text_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    image_embedding_model: str = "openai/clip-vit-base-patch32"
    audio_model: str = "openai/whisper-medium"
    
    # FAISS
    faiss_index_path: str = "./data/faiss_indices"
    text_index_name: str = "text_embeddings.index"
    image_index_name: str = "image_embeddings.index"
    audio_index_name: str = "audio_embeddings.index"
    
    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50
    spacy_model: str = "en_core_web_sm"
    
    # RAG
    top_k_results: int = 5
    max_context_length: int = 2048
    temperature: float = 0.7
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
