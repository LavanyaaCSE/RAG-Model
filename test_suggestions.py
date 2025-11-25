from backend.rag_service import generate_suggestions
import logging

logging.basicConfig(level=logging.INFO)

chunks = [
    {"content": "The quick brown fox jumps over the lazy dog. This is a test sentence."},
    {"content": "Python is a programming language. It is widely used for web development and data science."}
]

print("Testing generate_suggestions...")
suggestions = generate_suggestions(chunks)
print(f"Result: {suggestions}")
