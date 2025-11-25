# Multimodal RAG System

An offline multimodal Retrieval-Augmented Generation (RAG) system that ingests, indexes, and queries diverse data formats (DOCX, PDF, Images, Audio) using Mistral LLM, FAISS vector search, PostgreSQL, MinIO, and a React-Vite frontend.

## Features

- **Multimodal Ingestion**: Process PDF, DOCX, images, and audio files
- **Semantic Search**: Cross-modal search across text, images, and audio
- **RAG with Citations**: Generate grounded answers with source citations
- **Offline Operation**: All models run locally (Mistral via Ollama)
- **Citation Transparency**: Track sources with page numbers and timestamps

## Architecture

```
Backend (FastAPI)
├── Document Processing (PDF/DOCX with spaCy chunking)
├── Image Processing (CLIP embeddings)
├── Audio Processing (Whisper transcription)
├── Vector Search (FAISS)
├── RAG Engine (Mistral via Ollama)
└── Storage (PostgreSQL + MinIO)

Frontend (React + Vite)
└── Unified search interface with citation display
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Ollama (for Mistral LLM)
- 16GB+ RAM recommended
- ~10GB disk space for models

## Setup

### 1. Install Ollama and Pull Mistral Model

```bash
# Install Ollama from https://ollama.ai
# Then pull the Mistral model
ollama pull mistral:7b-instruct
```

### 2. Start Infrastructure Services

```bash
# Start PostgreSQL and MinIO
docker-compose up -d
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Copy environment file
cp ../.env.example .env

# Run database migrations
python -c "from database import init_db; init_db()"

# Start backend server
uvicorn main_simple:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Usage

### Upload Documents

```bash
# Upload PDF/DOCX
curl -X POST http://localhost:8000/api/upload/document \
  -F "file=@document.pdf"

# Upload image
curl -X POST http://localhost:8000/api/upload/image \
  -F "file=@screenshot.png"

# Upload audio
curl -X POST http://localhost:8000/api/upload/audio \
  -F "file=@recording.mp3"
```

### Search

```bash
# Text search across all modalities
curl -X POST http://localhost:8000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "international development 2024", "top_k": 5}'
```

### Query with RAG

```bash
# Ask questions with grounded answers
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does the report say about international development?"}'
```

## API Endpoints

- `POST /api/upload/document` - Upload PDF/DOCX
- `POST /api/upload/image` - Upload images
- `POST /api/upload/audio` - Upload audio files
- `POST /api/search/text` - Search across modalities
- `POST /api/search/hybrid` - Hybrid search with query expansion
- `POST /api/query` - RAG-based question answering
- `GET /api/documents` - List all documents
- `GET /api/documents/{id}` - Get document details
- `DELETE /api/documents/{id}` - Delete document

## Configuration

Edit `.env` file to configure:

- Database connection
- MinIO credentials
- Ollama endpoint
- Model selections
- Chunking parameters
- RAG settings

## Project Structure

```
Offline-RAG/
├── backend/
│   ├── api/              # API endpoints
│   ├── models/           # Database models
│   ├── services/         # Core services
│   ├── config.py         # Configuration
│   ├── database.py       # Database connection
│   └── main.py           # FastAPI app
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   └── App.jsx       # Main app
│   └── package.json
├── docker-compose.yml    # Infrastructure services
└── README.md
```

## Troubleshooting

### Models not loading
- Ensure Ollama is running: `ollama list`
- Check disk space for model downloads
- Verify internet connection for first-time model downloads

### Database connection errors
- Ensure Docker containers are running: `docker-compose ps`
- Check PostgreSQL logs: `docker-compose logs postgres`

### Out of memory
- Reduce `chunk_size` in `.env`
- Use smaller models (e.g., `whisper-small` instead of `whisper-medium`)
- Reduce `top_k_results` for searches

## License

MIT
