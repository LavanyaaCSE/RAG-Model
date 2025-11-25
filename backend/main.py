"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from config import get_settings
from database import init_db
from api import upload_router, search_router, query_router, documents_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Multimodal RAG API...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Pre-load models
    from .services import (
        get_embedding_service,
        get_document_processor,
        get_rag_engine
    )
    
    logger.info("Loading embedding models...")
    embedding_service = get_embedding_service()
    logger.info("Embedding models loaded")
    
    logger.info("Loading document processor...")
    doc_processor = get_document_processor()
    logger.info("Document processor loaded")
    
    logger.info("Loading RAG engine...")
    rag_engine = get_rag_engine()
    logger.info("RAG engine loaded")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Multimodal RAG API",
    description="Offline multimodal Retrieval-Augmented Generation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
origins = settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload_router)
app.include_router(search_router)
app.include_router(query_router)
app.include_router(documents_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Multimodal RAG API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
