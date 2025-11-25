import { useState } from 'react';
import axios from 'axios';
import './ImageSearch.css';

function ImageSearch({ advancedFilters = null }) {
    const [file, setFile] = useState(null);
    const [preview, setPreview] = useState(null);
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
        const validTypes = ['.jpg', '.jpeg', '.png', '.gif', '.bmp'];
        const fileExt = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();

        if (!validTypes.includes(fileExt)) {
            alert('Please upload image files only (JPG, PNG, GIF, BMP)');
            return;
        }

        setFile(selectedFile);
        setResults(null);

        // Create preview
        const reader = new FileReader();
        reader.onloadend = () => {
            setPreview(reader.result);
        };
        reader.readAsDataURL(selectedFile);
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
            const response = await axios.post('http://localhost:8000/api/find-similar-image', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setResults(response.data);
        } catch (error) {
            console.error('Error finding similar images:', error);
            alert(`Error: ${error.response?.data?.detail || error.message}`);
        } finally {
            setLoading(false);
        }
    };

    const clearFile = () => {
        setFile(null);
        setPreview(null);
        setResults(null);
    };

    return (
        <div className="image-search">
            <div
                className={`upload-zone ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                {!file ? (
                    <>
                        <div className="upload-icon">🖼️</div>
                        <h3>Reverse Image Search</h3>
                        <p>Drag and drop an image or click to browse</p>
                        <input
                            type="file"
                            id="image-upload"
                            accept=".jpg,.jpeg,.png,.gif,.bmp"
                            onChange={handleFileInput}
                            style={{ display: 'none' }}
                        />
                        <label htmlFor="image-upload" className="btn btn-primary">
                            Choose Image
                        </label>
                        <p className="file-types">Supported: JPG, PNG, GIF, BMP</p>
                    </>
                ) : (
                    <div className="file-selected">
                        <div className="image-preview">
                            <img src={preview} alt="Preview" />
                        </div>
                        <div className="file-info">
                            <div className="file-name">{file.name}</div>
                            <div className="file-size">{(file.size / 1024).toFixed(2)} KB</div>
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
                <div className="image-results">
                    <h3>Similar Images ({results.similar_images.length})</h3>
                    {results.note && (
                        <div className="info-note">ℹ️ {results.note}</div>
                    )}
                    {results.similar_images.length === 0 ? (
                        <div className="no-results">
                            <p>No similar images found</p>
                        </div>
                    ) : (
                        <div className="image-grid">
                            {results.similar_images.map((img, index) => (
                                <div key={img.document_id} className="image-card glass-card">
                                    <div className="rank-badge">#{index + 1}</div>
                                    <div className="image-thumbnail">
                                        <img
                                            src={`http://localhost:8000${img.url}`}
                                            alt={img.filename}
                                            onError={(e) => {
                                                e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"/>';
                                                e.target.style.background = '#f0f0f0';
                                            }}
                                        />
                                    </div>
                                    <div className="image-info">
                                        <div className="image-name">{img.filename}</div>
                                        <div className="similarity-badge">
                                            {(img.similarity * 100).toFixed(0)}% Match
                                        </div>
                                    </div>
                                    <button
                                        className="btn-small btn-primary"
                                        onClick={() => window.open(`http://localhost:8000${img.url}`, '_blank')}
                                    >
                                        👁️ View
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default ImageSearch;
