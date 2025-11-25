"""RAG engine using Ollama for LLM inference."""
import ollama
from typing import List, Dict, Tuple
import logging
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGEngine:
    """Retrieval-Augmented Generation engine with Mistral LLM."""
    
    def __init__(self):
        """Initialize RAG engine."""
        self.client = ollama.Client(host=settings.ollama_base_url)
        self.model = settings.ollama_model
        
        # Verify model is available
        self._check_model()
    
    def _check_model(self):
        """Check if model is available."""
        try:
            models = self.client.list()
            available_models = [m['name'] for m in models.get('models', [])]
            
            if self.model not in available_models:
                logger.warning(f"Model {self.model} not found. Available models: {available_models}")
                logger.info(f"Pulling model {self.model}...")
                self.client.pull(self.model)
                logger.info(f"Model {self.model} pulled successfully")
            else:
                logger.info(f"Model {self.model} is available")
        except Exception as e:
            logger.error(f"Error checking model: {e}")
            raise
    
    def generate_answer(
        self,
        query: str,
        context_chunks: List[Dict],
        context_images: List[Dict] = None,
        context_audio: List[Dict] = None
    ) -> Dict:
        """
        Generate answer using retrieved context.
        
        Args:
            query: User query
            context_chunks: Retrieved text chunks with metadata
            context_images: Retrieved images with metadata
            context_audio: Retrieved audio segments with metadata
            
        Returns:
            Dictionary with answer and citations
        """
        # Build context string with citations
        context_parts = []
        citations = []
        citation_num = 1
        
        # Add text chunks
        if context_chunks:
            context_parts.append("## Relevant Text Documents:")
            for chunk in context_chunks:
                citation_id = f"[{citation_num}]"
                context_parts.append(f"\n{citation_id} {chunk['content']}")
                citations.append({
                    "id": citation_num,
                    "type": "text",
                    "source": chunk.get('filename', 'Unknown'),
                    "page": chunk.get('page_number'),
                    "chunk_id": chunk.get('chunk_id'),
                    "document_id": chunk.get('document_id')
                })
                citation_num += 1
        
        # Add image descriptions
        if context_images:
            context_parts.append("\n\n## Relevant Images:")
            for img in context_images:
                citation_id = f"[{citation_num}]"
                img_desc = f"Image: {img.get('filename', 'Unknown')}"
                if img.get('caption'):
                    img_desc += f" - {img['caption']}"
                context_parts.append(f"\n{citation_id} {img_desc}")
                citations.append({
                    "id": citation_num,
                    "type": "image",
                    "source": img.get('filename', 'Unknown'),
                    "image_id": img.get('image_id'),
                    "document_id": img.get('document_id'),
                    "url": img.get('url')
                })
                citation_num += 1
        
        # Add audio transcripts
        if context_audio:
            context_parts.append("\n\n## Relevant Audio Transcripts:")
            for audio in context_audio:
                citation_id = f"[{citation_num}]"
                time_range = f"{audio.get('start_time', 0):.1f}s - {audio.get('end_time', 0):.1f}s"
                context_parts.append(f"\n{citation_id} [{time_range}] {audio['transcript']}")
                citations.append({
                    "id": citation_num,
                    "type": "audio",
                    "source": audio.get('filename', 'Unknown'),
                    "start_time": audio.get('start_time'),
                    "end_time": audio.get('end_time'),
                    "segment_id": audio.get('segment_id'),
                    "document_id": audio.get('document_id')
                })
                citation_num += 1
        
        context_str = "\n".join(context_parts)
        
        # Build prompt
        prompt = self._build_prompt(query, context_str)
        
        # Generate answer
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": settings.temperature,
                    "num_predict": settings.max_context_length
                }
            )
            
            answer = response['response'].strip()
            
            return {
                "answer": answer,
                "citations": citations,
                "context_used": {
                    "text_chunks": len(context_chunks) if context_chunks else 0,
                    "images": len(context_images) if context_images else 0,
                    "audio_segments": len(context_audio) if context_audio else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Build prompt for LLM."""
        prompt = f"""You are a helpful AI assistant that answers questions based on the provided context. 
Your answers should be accurate, concise, and grounded in the given information.

IMPORTANT INSTRUCTIONS:
1. Answer the question using ONLY the information from the provided context
2. Include citation numbers [1], [2], etc. when referencing specific sources
3. If the context doesn't contain enough information to answer the question, say so
4. Be specific and provide relevant details from the context
5. If multiple sources support your answer, cite all of them

CONTEXT:
{context}

QUESTION: {query}

ANSWER (with citations):"""
        
        return prompt
    
    def expand_query(self, query: str) -> List[str]:
        """
        Generate query expansions for better retrieval.
        
        Args:
            query: Original query
            
        Returns:
            List of expanded queries
        """
        prompt = f"""Generate 3 alternative phrasings of the following query to improve search results.
Return only the alternative queries, one per line, without numbering or explanations.

Original query: {query}

Alternative queries:"""
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.7, "num_predict": 200}
            )
            
            expansions = [query]  # Include original
            for line in response['response'].strip().split('\n'):
                line = line.strip()
                if line and not line.startswith(('1.', '2.', '3.', '-')):
                    expansions.append(line)
            
            return expansions[:4]  # Original + 3 expansions
            
        except Exception as e:
            logger.warning(f"Error expanding query: {e}")
            return [query]  # Fallback to original


# Global instance
_rag_engine = None


def get_rag_engine() -> RAGEngine:
    """Get singleton RAG engine instance."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
