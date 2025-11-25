"""Vector store using FAISS for similarity search."""
import faiss
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import pickle
import logging
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStore:
    """FAISS-based vector store for embeddings."""
    
    def __init__(self, index_name: str, dimension: int):
        """
        Initialize vector store.
        
        Args:
            index_name: Name of the index file
            dimension: Embedding dimension
        """
        self.index_name = index_name
        self.dimension = dimension
        self.index_path = Path(settings.faiss_index_path) / index_name
        self.metadata_path = Path(settings.faiss_index_path) / f"{index_name}.metadata"
        
        # Create directory if it doesn't exist
        Path(settings.faiss_index_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize or load index
        self.index = self._load_or_create_index()
        self.id_mapping = self._load_metadata()
        
    def _load_or_create_index(self) -> faiss.Index:
        """Load existing index or create new one."""
        if self.index_path.exists():
            logger.info(f"Loading existing FAISS index: {self.index_path}")
            return faiss.read_index(str(self.index_path))
        else:
            logger.info(f"Creating new FAISS index: {self.index_path}")
            # Use IndexFlatIP for cosine similarity (after L2 normalization)
            index = faiss.IndexFlatIP(self.dimension)
            return index
    
    def _load_metadata(self) -> List[int]:
        """Load ID mapping metadata."""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'rb') as f:
                return pickle.load(f)
        return []
    
    def _save_index(self):
        """Save index to disk."""
        faiss.write_index(self.index, str(self.index_path))
        logger.info(f"Saved FAISS index: {self.index_path}")
    
    def _save_metadata(self):
        """Save metadata to disk."""
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.id_mapping, f)
        logger.info(f"Saved metadata: {self.metadata_path}")
    
    def add_embeddings(self, embeddings: np.ndarray, ids: List[int]):
        """
        Add embeddings to the index.
        
        Args:
            embeddings: Numpy array of embeddings (n, dimension)
            ids: List of database record IDs corresponding to embeddings
        """
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {embeddings.shape[1]}")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to index
        self.index.add(embeddings)
        
        # Update ID mapping
        self.id_mapping.extend(ids)
        
        # Save to disk
        self._save_index()
        self._save_metadata()
        
        logger.info(f"Added {len(ids)} embeddings to index. Total: {self.index.ntotal}")
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> Tuple[List[int], List[float]]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding (1, dimension) or (dimension,)
            k: Number of results to return
            
        Returns:
            Tuple of (database_ids, similarity_scores)
        """
        # Ensure query is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Normalize query
        faiss.normalize_L2(query_embedding)
        
        # Search
        k = min(k, self.index.ntotal)  # Don't search for more than available
        if k == 0:
            return [], []
        
        distances, indices = self.index.search(query_embedding, k)
        
        # Map FAISS indices to database IDs
        db_ids = [self.id_mapping[idx] for idx in indices[0] if idx < len(self.id_mapping)]
        scores = distances[0].tolist()
        
        return db_ids, scores
    
    def delete_by_ids(self, ids: List[int]):
        """
        Delete embeddings by database IDs.
        Note: FAISS doesn't support efficient deletion, so we rebuild the index.
        
        Args:
            ids: List of database IDs to delete
        """
        # Find indices to keep
        indices_to_keep = [i for i, db_id in enumerate(self.id_mapping) if db_id not in ids]
        
        if not indices_to_keep:
            # Delete all - create new empty index
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_mapping = []
        else:
            # Rebuild index with remaining vectors
            vectors = np.array([self.index.reconstruct(i) for i in indices_to_keep])
            self.id_mapping = [self.id_mapping[i] for i in indices_to_keep]
            
            # Create new index
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(vectors)
        
        # Save
        self._save_index()
        self._save_metadata()
        
        logger.info(f"Deleted {len(ids)} embeddings. Remaining: {self.index.ntotal}")
    
    def get_total_count(self) -> int:
        """Get total number of vectors in index."""
        return self.index.ntotal


class VectorStoreManager:
    """Manage multiple vector stores for different modalities."""
    
    def __init__(self, text_dim: int, image_dim: int):
        """
        Initialize vector store manager.
        
        Args:
            text_dim: Text embedding dimension
            image_dim: Image embedding dimension
        """
        self.text_store = VectorStore(settings.text_index_name, text_dim)
        self.image_store = VectorStore(settings.image_index_name, image_dim)
        self.audio_store = VectorStore(settings.audio_index_name, text_dim)  # Audio uses text embeddings
    
    def get_store(self, modality: str) -> VectorStore:
        """Get vector store for specific modality."""
        if modality == "text":
            return self.text_store
        elif modality == "image":
            return self.image_store
        elif modality == "audio":
            return self.audio_store
        else:
            raise ValueError(f"Unknown modality: {modality}")


# Global instance
_vector_store_manager = None


def get_vector_store_manager(text_dim: int = 384, image_dim: int = 512) -> VectorStoreManager:
    """Get singleton vector store manager instance."""
    global _vector_store_manager
    if _vector_store_manager is None:
        _vector_store_manager = VectorStoreManager(text_dim, image_dim)
    return _vector_store_manager
