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
                "full_content": chunk["content"],  # Full chunk for "View Context"
                "similarity": chunk.get("similarity", 0.0),
                "document_id": chunk.get("document_id"),  # For opening document
                "chunk_index": chunk.get("chunk_index", 0)  # For page navigation
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
        
        # Check if the model couldn't find the answer in the documents
        cannot_answer_phrases = [
            "cannot find",
            "not found in",
            "no information",
            "don't have information",
            "doesn't contain",
            "not mentioned",
            "not available in"
        ]
        
        answer_lower = answer.lower()
        cannot_answer = any(phrase in answer_lower for phrase in cannot_answer_phrases)
        
        logger.info(f"Generated answer for question: {question[:50]}...")
        
        return {
            "answer": answer,
            "citations": [] if cannot_answer else citations,  # Clear citations if can't answer
            "context_used": {
                "text_chunks": 0 if cannot_answer else len(context_chunks),
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


def generate_suggestions(chunks: list[dict]) -> list[str]:
    """Generate suggested questions based on document chunks."""
    try:
        if not chunks:
            return []
            
        # Prepare context
        context_text = "\n\n".join([c["content"][:500] for c in chunks])
        
        prompt = f"""Based on the following text snippets from a user's documents, generate 3 short, specific, and interesting questions that a user might ask to learn more about this content.
        
Text Snippets:
{context_text}

Generate ONLY the 3 questions, one per line. Do not number them. Do not add any other text."""

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7}
        )
        
        content = response['message']['content'].strip()
        logger.info(f"Raw suggestions content: {content}")
        
        questions = [q.strip("- ").strip() for q in content.split('\n') if q.strip()]
        
        # Filter out garbage or too long questions
        valid_questions = [q for q in questions if len(q) < 150 and "?" in q]
        
        if not valid_questions:
            logger.warning(f"No valid questions after filtering. Raw questions: {questions}")
        
        return valid_questions[:3]
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        return []
