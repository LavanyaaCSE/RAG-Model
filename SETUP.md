# Multimodal RAG System - Setup Guide

This guide will help you set up and run the Multimodal RAG system.

## Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.9+**
   - Download from https://www.python.org/downloads/
   - Verify: `python --version`

2. **Node.js 18+**
   - Download from https://nodejs.org/
   - Verify: `node --version`

3. **Docker Desktop**
   - Download from https://www.docker.com/products/docker-desktop/
   - Start Docker Desktop before proceeding

4. **Ollama**
   - Download from https://ollama.ai/
   - Install and start Ollama

## Step-by-Step Setup

### 1. Install Ollama and Pull Mistral Model

```bash
# After installing Ollama, pull the Mistral model
ollama pull mistral:7b-instruct

# Verify the model is installed
ollama list
```

### 2. Start Infrastructure Services

```bash
# Navigate to project root
cd d:\Offline-RAG

# Start PostgreSQL and MinIO using Docker Compose
docker-compose up -d

# Verify containers are running
docker-compose ps
```

You should see:
- `rag_postgres` - PostgreSQL database
- `rag_minio` - MinIO object storage

### 3. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install Python dependencies (this may take several minutes)
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm

# Initialize database
python -c "from database import init_db; init_db()"

# Create data directory for FAISS indices
mkdir data
mkdir data\faiss_indices
```

### 4. Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd d:\Offline-RAG\frontend

# Install Node.js dependencies
npm install
```

### 5. Start the Application

You'll need **three terminal windows**:

**Terminal 1 - Backend API:**
```bash
cd d:\Offline-RAG\backend
venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Wait for the message: "Application startup complete"

**Terminal 2 - Frontend:**
```bash
cd d:\Offline-RAG\frontend
npm run dev
```

**Terminal 3 - Ollama (if not running as service):**
```bash
ollama serve
```

### 6. Access the Application

Open your browser and navigate to:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (login: minioadmin / minioadmin123)

## First Steps

1. **Upload Documents**
   - Click "Upload Files" on the home page
   - Drag and drop or select PDF, DOCX, images, or audio files
   - Wait for processing to complete

2. **Search**
   - Enter a question in the search box
   - Select which modalities to search (Documents, Images, Audio)
   - View results with citations

3. **View Documents**
   - Navigate to "Documents" page
   - Filter by type
   - View or delete documents

## Troubleshooting

### Backend won't start

**Issue**: Models not loading
```bash
# Check if Ollama is running
ollama list

# If Mistral is not listed, pull it
ollama pull mistral:7b-instruct
```

**Issue**: Database connection error
```bash
# Check if Docker containers are running
docker-compose ps

# If not running, start them
docker-compose up -d

# Check PostgreSQL logs
docker-compose logs postgres
```

**Issue**: Out of memory
- Reduce `CHUNK_SIZE` in `.env` to 256
- Use `whisper-small` instead of `whisper-medium`
- Close other applications

### Frontend won't start

**Issue**: Port 5173 already in use
```bash
# Kill the process using port 5173
# On Windows:
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# On macOS/Linux:
lsof -ti:5173 | xargs kill -9
```

**Issue**: Cannot connect to backend
- Ensure backend is running on port 8000
- Check CORS settings in backend `.env`

### Upload fails

**Issue**: MinIO connection error
```bash
# Check MinIO is running
docker-compose ps

# Restart MinIO
docker-compose restart minio
```

**Issue**: File too large
- Check available disk space
- Increase Docker resource limits in Docker Desktop settings

### Search returns no results

**Issue**: No documents uploaded
- Upload documents first via the Upload page

**Issue**: Documents still processing
- Wait for processing to complete (check Documents page for status)

**Issue**: FAISS index not created
```bash
# Check if data directory exists
ls data/faiss_indices

# If missing, create it
mkdir -p data/faiss_indices
```

## Stopping the Application

1. Stop frontend: Press `Ctrl+C` in frontend terminal
2. Stop backend: Press `Ctrl+C` in backend terminal
3. Stop Docker services:
```bash
docker-compose down
```

## Restarting

To restart the application later:

```bash
# Start Docker services
docker-compose up -d

# Start backend (in backend directory with venv activated)
uvicorn main:app --reload

# Start frontend (in frontend directory)
npm run dev
```

## Configuration

Edit `.env` file in the root directory to customize:
- Model selections
- Chunking parameters
- Database credentials
- API settings

## Getting Help

- Check logs in backend terminal for errors
- View browser console for frontend errors
- Check Docker logs: `docker-compose logs`
- Verify all services are running: `docker-compose ps`

## System Requirements

- **RAM**: 16GB+ recommended
- **Disk Space**: ~15GB (10GB for models, 5GB for data)
- **GPU**: Optional (CPU mode works but slower)
- **Internet**: Required for first-time model downloads
