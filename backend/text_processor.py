"""Text processing service - simplified version."""
import PyPDF2
import pdfplumber
from docx import Document as DocxDocument
import spacy
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("Loaded spaCy model successfully")
except Exception as e:
    logger.error(f"Error loading spaCy model: {e}")
    nlp = None


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file."""
    text = ""
    
    try:
        # Try pdfplumber first
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
    except Exception as e:
        logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
        
        # Fallback to PyPDF2
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
        except Exception as e2:
            logger.error(f"PyPDF2 also failed: {e2}")
            raise
    
    return text.strip()


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from DOCX file."""
    doc = DocxDocument(file_path)
    text = "\n\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
    return text


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[dict]:
    """Chunk text using spaCy token-based chunking."""
    if not nlp:
        # Fallback to simple chunking if spaCy not available
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunks.append({
                "content": " ".join(chunk_words),
                "chunk_index": len(chunks),
                "token_count": len(chunk_words)
            })
        return chunks
    
    # Process with spaCy
    doc = nlp(text)
    tokens = [token.text for token in doc]
    
    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i:i + chunk_size]
        chunks.append({
            "content": " ".join(chunk_tokens),
            "chunk_index": len(chunks),
            "token_count": len(chunk_tokens)
        })
    
    return chunks



import re

def extract_metadata_from_text(text: str) -> dict:
    """Extract comprehensive metadata using spaCy NER and regex patterns."""
    metadata = {
        "emails": [],
        "phone_numbers": [],
        "dates": [],
        "addresses": [],
        "organizations": [],
        "persons": [],
        "locations": []
    }
    
    # Extract emails using regex
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    metadata["emails"] = list(set(re.findall(email_pattern, text)))
    
    # Extract phone numbers using regex (supports multiple formats)
    phone_patterns = [
        r'\b\d{10}\b',  # 10 digits
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # XXX-XXX-XXXX or XXX.XXX.XXXX
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',  # (XXX) XXX-XXXX
        r'\+\d{1,3}[-.\s]?\d{1,14}',  # International format
    ]
    for pattern in phone_patterns:
        metadata["phone_numbers"].extend(re.findall(pattern, text))
    metadata["phone_numbers"] = list(set(metadata["phone_numbers"]))
    
    # Use spaCy NER for entity extraction
    if nlp:
        try:
            doc = nlp(text)
            
            for ent in doc.ents:
                if ent.label_ == "DATE":
                    metadata["dates"].append(ent.text)
                elif ent.label_ == "GPE":  # Geo-political entity (cities, countries)
                    metadata["locations"].append(ent.text)
                elif ent.label_ == "LOC":  # Non-GPE locations
                    metadata["addresses"].append(ent.text)
                elif ent.label_ == "ORG":  # Organizations
                    metadata["organizations"].append(ent.text)
                elif ent.label_ == "PERSON":  # Person names
                    metadata["persons"].append(ent.text)
            
            # Deduplicate lists
            for key in ["dates", "locations", "addresses", "organizations", "persons"]:
                metadata[key] = list(set(metadata[key]))
                
        except Exception as e:
            logger.warning(f"Error in NER extraction: {e}")
    
    # Remove empty lists for cleaner output
    metadata = {k: v for k, v in metadata.items() if v}
    
    return metadata


def process_document(file_path: Path, file_type: str) -> dict:
    """Process document and return text and chunks."""
    try:
        # Extract text
        if file_type in ["pdf"]:
            text = extract_text_from_pdf(file_path)
        elif file_type in ["docx", "doc"]:
            text = extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Extract metadata (emails, etc.)
        metadata = extract_metadata_from_text(text)
        
        # Chunk text
        chunks = chunk_text(text)
        
        return {
            "text": text,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "total_tokens": sum(c["token_count"] for c in chunks),
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise
