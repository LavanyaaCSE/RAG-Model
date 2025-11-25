"""RAG service with Ollama and Mistral - simplified version."""
import ollama
import logging

logger = logging.getLogger(__name__)

# Ollama client
OLLAMA_MODEL = "mistral:7b-instruct"


def generate_answer(question: str, context_chunks: list[dict]) -> dict:
    """Generate answer using RAG with Mistral."""
    try:
        # Build context from chunks
        context_parts = []
        citations = []
        
        for i, chunk in enumerate(context_chunks, 1):
            context_parts.append(f"[{i}] {chunk['content']}")
            citations.append({
                "id": i,
                "source": chunk.get("filename", "Unknown"),
                "type": "text",
                "content": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"],
                "similarity": chunk.get("similarity", 0.0)
            })
            
            # Add metadata context if available
            if chunk.get("metadata"):
                meta = chunk["metadata"]
                metadata_lines = []
                
                if meta.get("emails"):
                    metadata_lines.append(f"📧 Emails: {', '.join(meta['emails'])}")
                if meta.get("phone_numbers"):
                    metadata_lines.append(f"📞 Phone Numbers: {', '.join(meta['phone_numbers'])}")
                if meta.get("dates"):
                    metadata_lines.append(f"📅 Dates: {', '.join(meta['dates'][:5])}")  # Limit to 5
                if meta.get("locations"):
                    metadata_lines.append(f"📍 Locations: {', '.join(meta['locations'][:5])}")
                if meta.get("addresses"):
                    metadata_lines.append(f"🏠 Addresses: {', '.join(meta['addresses'][:5])}")
                if meta.get("organizations"):
                    metadata_lines.append(f"🏢 Organizations: {', '.join(meta['organizations'][:5])}")
                if meta.get("persons"):
                    metadata_lines.append(f"👤 Persons: {', '.join(meta['persons'][:5])}")
                
                if metadata_lines:
                    metadata_text = "\n".join(metadata_lines)
                    context_parts.append(f"[Extracted Metadata from {chunk.get('filename', 'document')}]\n{metadata_text}")
        
        context_text = "\n\n".join(context_parts)
        logger.info(f"RAG Context:\n{context_text}")
        
        # Create prompt
        prompt = f"""You are a precise AI assistant. Answer the question strictly using ONLY the provided context.
If the answer is not found in the context, say "I cannot find the answer in the provided documents."
Do not use outside knowledge. Use citations [1], [2], etc. to reference the sources.

Context:
{context_text}

Question: {question}

Answer (include citations):"""
        
        # Generate response with Ollama
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{
                "role": "user",
                "content": prompt
            }],
            options={
                "temperature": 0.1,
                "num_predict": 512
            }
        )
        
        answer = response['message']['content']
        
        logger.info(f"Generated answer for question: {question[:50]}...")
        
        return {
            "answer": answer,
            "citations": citations,
            "context_used": {
                "text_chunks": len(context_chunks),
                "images": 0,
                "audio_segments": 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return {
            "answer": f"Error generating answer: {str(e)}. Make sure Ollama is running with the Mistral model.",
            "citations": [],
            "context_used": {
                "text_chunks": 0,
                "images": 0,
                "audio_segments": 0
            }
        }
