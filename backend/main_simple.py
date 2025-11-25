from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from minio.error import S3Error
import logging
import uuid
from pathlib import Path
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Multimodal RAG API",
    description="Offline multimodal Retrieval-Augmented Generation system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MinIO client
minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin123",
    secure=False
)

# Ensure bucket exists
BUCKET_NAME = "rag-documents"
try:
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)
        logger.info(f"Created MinIO bucket: {BUCKET_NAME}")
except S3Error as e:
    logger.error(f"MinIO error: {e}")

# Temporary upload directory
UPLOAD_DIR = Path("./temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Persistence directory
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

# In-memory document storage
documents_store = []


def save_metadata():
    """Save document metadata to JSON."""
    try:
        import json
        # Convert datetime objects to string if needed, currently they are created as default but we store them as is?
        # In models_simple.py we used SQLAlchemy, here we used dicts.
        # Let's ensure we serialize correctly.
        
        # Helper to serialize datetime
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError (f"Type {type(obj)} not serializable")

        with open(DATA_DIR / "documents.json", "w") as f:
            json.dump(documents_store, f, default=json_serial, indent=2)
        logger.info(f"Saved {len(documents_store)} documents to metadata")
    except Exception as e:
        logger.error(f"Error saving metadata: {e}")


def load_metadata():
    """Load document metadata from JSON."""
    global documents_store
    try:
        if (DATA_DIR / "documents.json").exists():
            import json
            with open(DATA_DIR / "documents.json", "r") as f:
                documents_store = json.load(f)
            logger.info(f"Loaded {len(documents_store)} documents from metadata")
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")


@app.on_event("startup")
async def startup_event():
    """Load state on startup."""
    load_metadata()
    try:
        from embedding_service import load_state
        load_state(DATA_DIR)
    except Exception as e:
        logger.error(f"Error loading embedding state: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Save state on shutdown."""
    save_metadata()
    try:
        from embedding_service import save_state
        save_state(DATA_DIR)
    except Exception as e:
        logger.error(f"Error saving embedding state: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Multimodal RAG API",
        "version": "1.0.0",
        "status": "running",
        "features": ["file_upload", "minio_storage", "persistence"],
        "documents_count": len(documents_store)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "minio": "connected"}


@app.get("/api/documents")
async def list_documents():
    """List all documents."""
    return documents_store


@app.post("/api/upload/document")
async def upload_document(file: UploadFile = File(...)):
    """Upload PDF or DOCX document."""
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
        minio_path = f"documents/{unique_filename}"
        minio_client.fput_object(BUCKET_NAME, minio_path, str(temp_path))
        
        # Store in memory
        doc_info = {
            "id": len(documents_store) + 1,
            "filename": unique_filename,
            "original_filename": file.filename,
            "file_type": file_ext[1:],
            "modality": "text",
            "file_size": temp_path.stat().st_size,
            "minio_path": minio_path,
            "processed": 1  # Processing
        }
        documents_store.append(doc_info)
        
        # Process document (extract text and chunk)
        try:
            from text_processor import process_document
            from embedding_service import add_chunks_to_index
            
            result = process_document(temp_path, file_ext[1:])
            
            # Store chunks in document
            doc_info["chunks"] = result["chunks"]
            doc_info["chunk_count"] = result["chunk_count"]
            
            # Generate embeddings and add to FAISS index
            add_chunks_to_index(doc_info["id"], result["chunks"])
            
            doc_info["processed"] = 2  # Completed
            
            # Save state
            from embedding_service import save_state
            save_state(DATA_DIR)
            save_metadata()
            
            logger.info(f"Processed document: {file.filename} - {result['chunk_count']} chunks, indexed")
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            doc_info["processed"] = 3  # Failed
        
        # Clean up temp file
        temp_path.unlink()
        
        return {
            "message": "Document uploaded and processed successfully",
            "document_id": doc_info["id"],
            "filename": file.filename,
            "chunks": doc_info.get("chunk_count", 0),
            "status": "processed" if doc_info["processed"] == 2 else "uploaded"
        }
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """Upload image file."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
        raise HTTPException(status_code=400, detail="Only image files are supported")
    
    try:
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = UPLOAD_DIR / unique_filename
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        minio_path = f"images/{unique_filename}"
        minio_client.fput_object(BUCKET_NAME, minio_path, str(temp_path))
        
        doc_info = {
            "id": len(documents_store) + 1,
            "filename": unique_filename,
            "original_filename": file.filename,
            "file_type": file_ext[1:],
            "modality": "image",
            "file_size": temp_path.stat().st_size,
            "minio_path": minio_path,
            "processed": 0
        }
        documents_store.append(doc_info)
        
        temp_path.unlink()
        
        logger.info(f"Uploaded image: {file.filename}")
        
        return {
            "message": "Image uploaded successfully",
            "document_id": doc_info["id"],
            "filename": file.filename,
            "status": "uploaded"
        }
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".mp3", ".wav", ".m4a", ".flac", ".ogg"]:
        raise HTTPException(status_code=400, detail="Only audio files are supported")
    
    try:
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        temp_path = UPLOAD_DIR / unique_filename
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        minio_path = f"audio/{unique_filename}"
        minio_client.fput_object(BUCKET_NAME, minio_path, str(temp_path))
        
        doc_info = {
            "id": len(documents_store) + 1,
            "filename": unique_filename,
            "original_filename": file.filename,
            "file_type": file_ext[1:],
            "modality": "audio",
            "file_size": temp_path.stat().st_size,
            "minio_path": minio_path,
            "processed": 0
        }
        documents_store.append(doc_info)
        
        temp_path.unlink()
        
        logger.info(f"Uploaded audio: {file.filename}")
        
        return {
            "message": "Audio uploaded successfully",
            "document_id": doc_info["id"],
            "filename": file.filename,
            "status": "uploaded"
        }
        
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: int):
    """Delete a document."""
    global documents_store
    doc = next((d for d in documents_store if d["id"] == document_id), None)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Delete from MinIO
        minio_client.remove_object(BUCKET_NAME, doc["minio_path"])
        
        # Remove from store
        documents_store = [d for d in documents_store if d["id"] != document_id]
        
        save_metadata()
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/download")
async def get_download_url(document_id: int):
    """Get URL to view document inline."""
    # Return a direct link to our proxy endpoint
    # This avoids MinIO presigned URL issues and gives us full control over headers
    return {
        "url": f"http://localhost:8000/api/documents/{document_id}/content",
        "filename": "document" 
    }


@app.get("/api/documents/{document_id}/content")
async def get_document_content(document_id: int):
    """Stream document content directly from MinIO."""
    doc = next((d for d in documents_store if d["id"] == document_id), None)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        from fastapi.responses import StreamingResponse
        
        # Get object from MinIO
        response = minio_client.get_object(BUCKET_NAME, doc["minio_path"])
        
        # Determine content type
        content_type = "application/octet-stream"
        if doc["filename"].endswith(".pdf"):
            content_type = "application/pdf"
        elif doc["filename"].endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif doc["filename"].endswith(".png"):
            content_type = "image/png"
            
        # Stream response
        return StreamingResponse(
            response.stream(32*1024),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{doc["original_filename"]}"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error streaming document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}/chunks")
async def get_document_chunks(document_id: int):
    """Get chunks for a document."""
    doc = next((d for d in documents_store if d["id"] == document_id), None)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc.get("chunks", [])


@app.post("/api/query/")
async def query(request: dict):
    """Query endpoint with RAG."""
    question = request.get("question", "")
    top_k = request.get("top_k", 5)
    
    if not question:
        return {
            "answer": "Please provide a question.",
            "citations": [],
            "context_used": {"text_chunks": 0, "images": 0, "audio_segments": 0}
        }
    
    try:
        from embedding_service import search_similar_chunks, get_index_stats
        from rag_service import generate_answer
        
        # Check if we have any indexed documents
        stats = get_index_stats()
        if stats["total_vectors"] == 0:
            return {
                "answer": f"No documents have been uploaded yet. Please upload some documents first to ask questions about them.",
                "citations": [],
                "context_used": {"text_chunks": 0, "images": 0, "audio_segments": 0}
            }
        
        # Search for relevant chunks
        search_results = search_similar_chunks(question, top_k)
        
        if not search_results:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "citations": [],
                "context_used": {"text_chunks": 0, "images": 0, "audio_segments": 0}
            }
        
        # Enrich with document info
        enriched_chunks = []
        for result in search_results:
            doc = next((d for d in documents_store if d["id"] == result["doc_id"]), None)
            if doc:
                enriched_chunks.append({
                    "content": result["content"],
                    "filename": doc["original_filename"],
                    "similarity": result["similarity"],
                    "metadata": doc.get("metadata", {})
                })
        
        # Generate answer using RAG
        rag_result = generate_answer(question, enriched_chunks)
        
        return rag_result
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        return {
            "answer": f"Error processing query: {str(e)}",
            "citations": [],
            "context_used": {"text_chunks": 0, "images": 0, "audio_segments": 0}
        }


@app.post("/api/search/text")
async def search_text(request: dict):
    """Search endpoint with semantic search."""
    query = request.get("query", "")
    top_k = request.get("top_k", 5)
    
    if not query:
        return []
    
    try:
        from embedding_service import search_similar_chunks, get_index_stats
        
        # Get index stats
        stats = get_index_stats()
        if stats["total_vectors"] == 0:
            return []
        
        # Search
        results = search_similar_chunks(query, top_k)
        
        # Enrich with document info
        enriched_results = []
        for result in results:
            doc = next((d for d in documents_store if d["id"] == result["doc_id"]), None)
            if doc:
                enriched_results.append({
                    "document_id": doc["id"],
                    "filename": doc["original_filename"],
                    "modality": doc["modality"],
                    "chunk_index": result["chunk_index"],
                    "content": result["content"],
                    "similarity": result["similarity"]
                })
        
        return enriched_results
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
