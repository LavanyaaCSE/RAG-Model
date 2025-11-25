"""Embedding service for text, images, and audio."""
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
from typing import List, Union
import logging
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """Unified embedding generation for all modalities."""
    
    def __init__(self):
        """Initialize embedding models."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Text embeddings
        logger.info(f"Loading text embedding model: {settings.text_embedding_model}")
        self.text_model = SentenceTransformer(settings.text_embedding_model)
        self.text_model.to(self.device)
        
        # Image embeddings (CLIP)
        logger.info(f"Loading image embedding model: {settings.image_embedding_model}")
        self.clip_model = CLIPModel.from_pretrained(settings.image_embedding_model)
        self.clip_processor = CLIPProcessor.from_pretrained(settings.image_embedding_model)
        self.clip_model.to(self.device)
        
    def embed_text(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text.
        
        Args:
            texts: Single text or list of texts
            
        Returns:
            Numpy array of embeddings (n_texts, embedding_dim)
        """
        if isinstance(texts, str):
            texts = [texts]
            
        embeddings = self.text_model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32
        )
        
        return embeddings
    
    def embed_image(self, images: Union[Image.Image, List[Image.Image]]) -> np.ndarray:
        """
        Generate embeddings for images using CLIP.
        
        Args:
            images: Single PIL Image or list of PIL Images
            
        Returns:
            Numpy array of embeddings (n_images, embedding_dim)
        """
        if isinstance(images, Image.Image):
            images = [images]
        
        # Process images
        inputs = self.clip_processor(images=images, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get image embeddings
        with torch.no_grad():
            image_features = self.clip_model.get_image_features(**inputs)
            
        # Normalize embeddings
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        return image_features.cpu().numpy()
    
    def embed_text_for_image_search(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generate text embeddings compatible with image embeddings (CLIP text encoder).
        Used for text-to-image search.
        
        Args:
            texts: Single text or list of texts
            
        Returns:
            Numpy array of embeddings (n_texts, embedding_dim)
        """
        if isinstance(texts, str):
            texts = [texts]
        
        # Process text
        inputs = self.clip_processor(text=texts, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get text embeddings
        with torch.no_grad():
            text_features = self.clip_model.get_text_features(**inputs)
            
        # Normalize embeddings
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        return text_features.cpu().numpy()
    
    def compute_similarity(self, embeddings1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between two sets of embeddings.
        
        Args:
            embeddings1: First set of embeddings (n1, dim)
            embeddings2: Second set of embeddings (n2, dim)
            
        Returns:
            Similarity matrix (n1, n2)
        """
        # Normalize embeddings
        embeddings1 = embeddings1 / np.linalg.norm(embeddings1, axis=1, keepdims=True)
        embeddings2 = embeddings2 / np.linalg.norm(embeddings2, axis=1, keepdims=True)
        
        # Compute cosine similarity
        similarity = np.dot(embeddings1, embeddings2.T)
        
        return similarity
    
    def get_embedding_dimension(self, modality: str = "text") -> int:
        """
        Get the dimension of embeddings for a given modality.
        
        Args:
            modality: "text" or "image"
            
        Returns:
            Embedding dimension
        """
        if modality == "text":
            return self.text_model.get_sentence_embedding_dimension()
        elif modality == "image":
            return self.clip_model.config.projection_dim
        else:
            raise ValueError(f"Unknown modality: {modality}")


# Global instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
