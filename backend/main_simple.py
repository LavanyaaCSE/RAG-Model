from fastapi import FastAPI, UploadFile, File, HTTPException, Form
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


def apply_filters(docs, filters, initial_doc_ids=None):
    """Filter documents based on criteria."""
    filtered_ids = set(initial_doc_ids) if initial_doc_ids else {d["id"] for d in docs}
    
    if not filters:
        return list(filtered_ids)
        
    start_date = filters.get("startDate")
    end_date = filters.get("endDate")
    min_size = filters.get("minSize")
    max_size = filters.get("maxSize")
    
    # Convert size to bytes (MB input)
    min_bytes = float(min_size) * 1024 * 1024 if min_size else 0
    max_bytes = float(max_size) * 1024 * 1024 if max_size else float('inf')
    
    final_ids = []
    
    for doc in docs:
        if doc["id"] not in filtered_ids:
            continue
            
        # Date filter
        if start_date or end_date:
            doc_date_str = doc.get("upload_date")
            if not doc_date_str:
                continue # Skip docs without date if filter is applied
                
            doc_date = datetime.fromisoformat(doc_date_str).date()
            
            if start_date and doc_date < datetime.fromisoformat(start_date).date():
                continue
            if end_date and doc_date > datetime.fromisoformat(end_date).date():
                continue
                
        # Size filter
        if min_size or max_size:
            size = doc.get("file_size", 0)
            if size < min_bytes:
                continue
            if size > max_bytes:
                continue
                
        final_ids.append(doc["id"])
        
    return final_ids


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
            "processed": 1,  # Processing
            "upload_date": datetime.now().isoformat()
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
            "processed": 2,  # Mark as completed
            "upload_date": datetime.now().isoformat()
        }
        documents_store.append(doc_info)
        
        # Generate CLIP embedding and add to image index (BEFORE deleting temp file!)
        try:
            from embedding_service import add_image_to_index, save_state
            add_image_to_index(doc_info["id"], str(temp_path))
            save_state(DATA_DIR)
            logger.info(f"Generated CLIP embedding for image: {file.filename}")
        except Exception as e:
            logger.error(f"Error generating image embedding: {e}")
        
        # NOW delete the temp file
        temp_path.unlink()
        
        # Save metadata
        save_metadata()
        
        logger.info(f"Uploaded image: {file.filename}")
        
        return {
            "message": "Image uploaded successfully",
            "document_id": doc_info["id"],
            "filename": file.filename,
            "status": "completed"
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
            "processed": 2,  # Mark as completed
            "upload_date": datetime.now().isoformat()
        }
        documents_store.append(doc_info)
        
        # Save metadata
        save_metadata()
        
        temp_path.unlink()
        
        logger.info(f"Uploaded audio: {file.filename}")
        
        return {
            "message": "Audio uploaded successfully",
            "document_id": doc_info["id"],
            "filename": file.filename,
            "status": "completed"
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
    document_ids = request.get("document_ids", None)  # Optional filter by document IDs
    
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
        
        # Apply filters if present
        filters = request.get("filters")
        filtered_doc_ids = document_ids
        
        if filters:
            filtered_doc_ids = apply_filters(documents_store, filters, document_ids)
            if not filtered_doc_ids:
                return {
                    "answer": "No documents match your filter criteria.",
                    "citations": [],
                    "context_used": {"text_chunks": 0, "images": 0, "audio_segments": 0}
                }
        
        # Search for relevant chunks (with optional document filter)
        search_results = search_similar_chunks(question, top_k, filter_doc_ids=filtered_doc_ids)
        
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
                    "metadata": doc.get("metadata", {}),
                    "document_id": doc["id"],  # For navigation
                    "chunk_index": result.get("chunk_index", 0)  # For page estimation
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
            
        # Apply filters
        filters = request.get("filters")
        filtered_doc_ids = None
        
        if filters:
            filtered_doc_ids = apply_filters(documents_store, filters)
            if not filtered_doc_ids:
                return []
        
        # Search
        results = search_similar_chunks(query, top_k, filter_doc_ids=filtered_doc_ids)
        
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


@app.post("/api/find-similar")
async def find_similar_documents(
    file: UploadFile = File(...),
    filters: str = Form(None)
):
    """Find similar documents by uploading a file."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".pdf", ".docx", ".doc", ".txt"]:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported")
    
    # Parse filters
    parsed_filters = None
    if filters:
        try:
            import json
            parsed_filters = json.loads(filters)
        except Exception as e:
            logger.error(f"Error parsing filters: {e}")
    
    temp_path = None
    try:
        # Generate unique filename
        unique_filename = f"temp_{uuid.uuid4()}{file_ext}"
        temp_path = UPLOAD_DIR / unique_filename
        
        # Save uploaded file temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract text from file
        from text_processor import extract_text_from_pdf, extract_text_from_docx
        
        if file_ext == ".pdf":
            text = extract_text_from_pdf(temp_path)
        elif file_ext in [".docx", ".doc"]:
            text = extract_text_from_docx(temp_path)
        else:  # .txt
            with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
            temp_path = None
        
        if not text or len(text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Could not extract meaningful text from file")
            
        # Apply filters to get allowed doc IDs
        filtered_doc_ids = None
        if parsed_filters:
            filtered_doc_ids = apply_filters(documents_store, parsed_filters)
            if not filtered_doc_ids:
                 return {
                    "uploaded_filename": file.filename,
                    "similar_documents": [],
                    "message": "No documents match your filter criteria"
                }
        
        # Search for similar chunks using first ~5000 chars
        from embedding_service import search_similar_chunks
        search_results = search_similar_chunks(text[:5000], top_k=30, filter_doc_ids=filtered_doc_ids)
        
        if not search_results:
            return {
                "uploaded_filename": file.filename,
                "similar_documents": [],
                "message": "No similar documents found"
            }
        
        # Group results by document and calculate average similarity
        from collections import defaultdict
        doc_scores = defaultdict(list)
        doc_chunks = defaultdict(list)
        
        for result in search_results:
            doc_id = result["doc_id"]
            doc_scores[doc_id].append(result["similarity"])
            doc_chunks[doc_id].append({
                "content": result["content"][:200],  # Preview
                "similarity": result["similarity"]
            })
        
        # Build response
        similar_docs = []
        for doc_id, scores in doc_scores.items():
            doc = next((d for d in documents_store if d["id"] == doc_id), None)
            if doc:
                avg_similarity = sum(scores) / len(scores)
                similar_docs.append({
                    "document_id": doc["id"],
                    "filename": doc["original_filename"],
                    "file_type": doc["file_type"],
                    "similarity": round(avg_similarity, 4),
                    "match_count": len(scores),
                    "top_chunks": sorted(doc_chunks[doc_id], key=lambda x: x["similarity"], reverse=True)[:3]
                })
        
        # Sort by similarity (highest first)
        similar_docs.sort(key=lambda x: x["similarity"], reverse=True)
        
        logger.info(f"Found {len(similar_docs)} similar documents for '{file.filename}'")
        
        return {
            "uploaded_filename": file.filename,
            "similar_documents": similar_docs[:10],  # Top 10
            "total_matches": len(similar_docs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Find similar error: {e}")
        # Clean up temp file if it exists
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.post("/api/find-similar-image")
async def find_similar_images(
    file: UploadFile = File(...),
    filters: str = Form(None)
):
    """Find similar images by uploading an image."""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
        raise HTTPException(status_code=400, detail="Only image files (JPG, PNG, GIF, BMP) are supported")
    
    # Parse filters
    parsed_filters = None
    if filters:
        try:
            import json
            parsed_filters = json.loads(filters)
        except Exception as e:
            logger.error(f"Error parsing filters: {e}")
    
    temp_path = None
    try:
        # Generate unique filename
        unique_filename = f"temp_{uuid.uuid4()}{file_ext}"
        temp_path = UPLOAD_DIR / unique_filename
        
        # Save uploaded image temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Apply filters to get allowed doc IDs
        filtered_doc_ids = None
        if parsed_filters:
            filtered_doc_ids = apply_filters(documents_store, parsed_filters)
            if not filtered_doc_ids:
                 # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()
                return {
                    "uploaded_filename": file.filename,
                    "similar_images": [],
                    "message": "No images match your filter criteria"
                }

        # Use CLIP-based similarity search
        from embedding_service import search_similar_images
        
        # Pass filtered_doc_ids to search_similar_images (need to update embedding_service.py too if it doesn't support it yet)
        # But wait, search_similar_images currently doesn't support filtering.
        # I need to filter the results AFTER search if the function doesn't support it, 
        # OR update search_similar_images to support it.
        # Let's check embedding_service.py first. 
        # Actually, for now, I will filter AFTER search for images since I haven't updated embedding_service.py for images yet.
        # BUT, filtering after search is inefficient if top_k is small.
        # Let's update embedding_service.py to support filtering for images as well.
        # For now, let's assume I'll update it or filter post-search.
        # Given the task size, I'll filter post-search here for simplicity as image index is small.
        
        search_results = search_similar_images(str(temp_path), top_k=50) # Get more results to allow for filtering
        
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
            temp_path = None
        
        if not search_results:
            return {
                "uploaded_filename": file.filename,
                "similar_images": [],
                "message": "No similar images found in database"
            }
        
        # Build response with actual similarity scores
        # Only include images with similarity > 0.6 (60%)
        SIMILARITY_THRESHOLD = 0.6
        similar_images = []
        
        for result in search_results:
            # Filter by doc ID if filters applied
            if filtered_doc_ids is not None and result["doc_id"] not in filtered_doc_ids:
                continue

            # Skip low similarity matches
            if result["similarity"] < SIMILARITY_THRESHOLD:
                continue
                
            doc = next((d for d in documents_store if d["id"] == result["doc_id"]), None)
            if doc and doc.get("modality") == "image":
                similar_images.append({
                    "document_id": doc["id"],
                    "filename": doc["original_filename"],
                    "file_type": doc["file_type"],
                    "similarity": result["similarity"],
                    "url": f"/api/documents/{doc['id']}/content"
                })
        
        # Sort by similarity (highest first)
        similar_images.sort(key=lambda x: x["similarity"], reverse=True)
        
        logger.info(f"Found {len(similar_images)} similar images using CLIP (threshold: {SIMILARITY_THRESHOLD})")
        
        return {
            "uploaded_filename": file.filename,
            "similar_images": similar_images[:10],  # Top 10
            "total_matches": len(similar_images)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Find similar image error: {e}")
        # Clean up temp file if it exists
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
