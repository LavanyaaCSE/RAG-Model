import { useState } from 'react';
import axios from 'axios';
import './SimilaritySearch.css';

function SimilaritySearch({ advancedFilters = null }) {
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(null);
    const [dragActive, setDragActive] = useState(false);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    };

    const handleFileSelect = (selectedFile) => {
        const validTypes = ['.pdf', '.docx', '.doc', '.txt'];
        const fileExt = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();

        if (!validTypes.includes(fileExt)) {
            alert('Please upload PDF, DOCX, or TXT files only');
            return;
        }

        setFile(selectedFile);
        setResults(null);
    };

    const handleFileInput = (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileSelect(e.target.files[0]);
        }
    };

    const handleSubmit = async () => {
        if (!file) return;

        setLoading(true);
        const formData = new FormData();
        formData.append('file', file);

        if (advancedFilters) {
            formData.append('filters', JSON.stringify(advancedFilters));
        }

        try {
            const response = await axios.post('http://localhost:8000/api/find-similar', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setResults(response.data);
        } catch (error) {
            console.error('Error finding similar documents:', error);
            alert(`Error: ${error.response?.data?.detail || error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const clearFile = () => {
        setFile(null);
        setResults(null);
    };

    return (
        <div className="similarity-search">
            <div
                className={`upload-zone ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                {!file ? (
                    <>
                        <div className="upload-icon">📤</div>
                        <h3>Find Similar Documents</h3>
                        <p>Drag and drop a file here or click to browse</p>
                        <input
                            type="file"
                            id="file-upload"
                            accept=".pdf,.docx,.doc,.txt"
                            onChange={handleFileInput}
                            style={{ display: 'none' }}
                        />
                        <label htmlFor="file-upload" className="btn btn-primary">
                            Choose File
                        </label>
                        <p className="file-types">Supported: PDF, DOCX, TXT</p>
                    </>
                ) : (
                    <div className="file-selected">
                        <div className="file-info">
                            <span className="file-icon">📄</span>
                            <div className="file-details">
                                <div className="file-name">{file.name}</div>
                                <div className="file-size">{(file.size / 1024).toFixed(2)} KB</div>
                            </div>
                        </div>
                        <div className="file-actions">
                            <button onClick={clearFile} className="btn-text">✕ Remove</button>
                            <button
                                onClick={handleSubmit}
                                className="btn btn-primary"
                                disabled={loading}
                            >
                                {loading ? 'Analyzing...' : '🔍 Find Similar'}
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {results && (
                <div className="similarity-results">
                    <h3>Similar Documents ({results.similar_documents.length})</h3>
                    {results.similar_documents.length === 0 ? (
                        <div className="no-results">
                            <p>No similar documents found</p>
                        </div>
                    ) : (
                        <div className="results-grid">
                            {results.similar_documents.map((doc, index) => (
                                <div key={doc.document_id} className="similarity-card glass-card">
                                    <div className="rank-badge">#{index + 1}</div>
                                    <div className="similarity-score">
                                        <div className="score-value">{(doc.similarity * 100).toFixed(1)}%</div>
                                        <div className="score-label">Match</div>
                                    </div>
                                    <div className="doc-info">
                                        <div className="doc-icon">📄</div>
                                        <div className="doc-name">{doc.filename}</div>
                                        <div className="doc-meta">
                                            {doc.match_count} matching sections
                                        </div>
                                    </div>
                                    <div className="doc-actions">
                                        <button
                                            className="btn-small btn-primary"
                                            onClick={() => window.open(`http://localhost:8000/api/documents/${doc.document_id}/content`, '_blank')}
                                        >
                                            📄 Open
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default SimilaritySearch;
