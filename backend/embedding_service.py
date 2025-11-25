"""Embedding and vector search service - simplified version."""
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from pathlib import Path
import pickle
import logging

logger = logging.getLogger(__name__)

# Load embedding model
try:
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    logger.info("Loaded SentenceTransformer model successfully")
except Exception as e:
    logger.error(f"Error loading embedding model: {e}")
    embedding_model = None

# FAISS index
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimension
faiss_index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product for cosine similarity
index_to_chunk_map = []  # Maps FAISS index to (doc_id, chunk_index)


def generate_embedding(text: str) -> np.ndarray:
    """Generate embedding for text."""
    if not embedding_model:
        # Return random embedding as fallback
        return np.random.rand(EMBEDDING_DIM).astype('float32')
    
    embedding = embedding_model.encode(text, convert_to_numpy=True)
    # Normalize for cosine similarity
    embedding = embedding / np.linalg.norm(embedding)
    return embedding.astype('float32')


def add_chunks_to_index(doc_id: int, chunks: list[dict]):
    """Add document chunks to FAISS index."""
    global faiss_index, index_to_chunk_map
    
    embeddings = []
    for chunk in chunks:
        embedding = generate_embedding(chunk["content"])
        embeddings.append(embedding)
        index_to_chunk_map.append({
            "doc_id": doc_id,
            "chunk_index": chunk["chunk_index"],
            "content": chunk["content"]
        })
    
    if embeddings:
        embeddings_array = np.array(embeddings)
        faiss_index.add(embeddings_array)
        logger.info(f"Added {len(embeddings)} chunks to FAISS index")


def search_similar_chunks(query: str, top_k: int = 5) -> list[dict]:
    """Search for similar chunks using FAISS."""
    if faiss_index.ntotal == 0:
        return []
    
    # Generate query embedding
    query_embedding = generate_embedding(query)
    query_embedding = np.array([query_embedding])
    
    # Search
    distances, indices = faiss_index.search(query_embedding, min(top_k, faiss_index.ntotal))
    
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(index_to_chunk_map):
            chunk_info = index_to_chunk_map[idx]
            results.append({
                "doc_id": chunk_info["doc_id"],
                "chunk_index": chunk_info["chunk_index"],
                "content": chunk_info["content"],
                "similarity": float(dist)
            })
    
    return results


def get_index_stats() -> dict:
    """Get FAISS index statistics."""
    return {
        "total_vectors": faiss_index.ntotal,
        "dimension": EMBEDDING_DIM,
        "total_chunks": len(index_to_chunk_map)
    }


def save_state(directory: Path):
    """Save FAISS index and chunk map to disk."""
    directory.mkdir(parents=True, exist_ok=True)
    
    # Save FAISS index
    faiss.write_index(faiss_index, str(directory / "faiss_index.bin"))
    
    # Save chunk map
    with open(directory / "chunk_map.pkl", "wb") as f:
        pickle.dump(index_to_chunk_map, f)
        
    logger.info(f"Saved FAISS index ({faiss_index.ntotal} vectors) and chunk map")


def load_state(directory: Path):
    """Load FAISS index and chunk map from disk."""
    global faiss_index, index_to_chunk_map
    
    try:
        if (directory / "faiss_index.bin").exists():
            faiss_index = faiss.read_index(str(directory / "faiss_index.bin"))
            logger.info(f"Loaded FAISS index with {faiss_index.ntotal} vectors")
            
        if (directory / "chunk_map.pkl").exists():
            with open(directory / "chunk_map.pkl", "rb") as f:
                index_to_chunk_map = pickle.load(f)
            logger.info(f"Loaded chunk map with {len(index_to_chunk_map)} entries")
            
    except Exception as e:
        logger.error(f"Error loading embedding state: {e}")
