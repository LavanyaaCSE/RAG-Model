import { useState } from 'react';
import SearchInterface from '../components/SearchInterface';
import ResultsDisplay from '../components/ResultsDisplay';
import UploadManager from '../components/UploadManager';
import './Home.css';

function Home() {
    const [results, setResults] = useState(null);
    const [showUpload, setShowUpload] = useState(false);

    const handleResults = (data) => {
        setResults(data);
    };

    const handleUploadComplete = () => {
        // Optionally refresh document list or show notification
        console.log('Upload complete');
    };

    return (
        <div className="home-page">
            <div className="container">
                {/* Hero Section */}
                <div className="hero-section">
                    <h1 className="hero-title animate-fade-in">
                        Multimodal RAG System
                    </h1>
                    <p className="hero-subtitle animate-fade-in">
                        Search across documents, images, and audio with AI-powered semantic understanding
                    </p>

                    <div className="hero-features flex gap-lg">
                        <div className="feature-card glass-card">
                            <span className="feature-icon">📄</span>
                            <h4>Document Search</h4>
                            <p>PDF and DOCX with intelligent chunking</p>
                        </div>
                        <div className="feature-card glass-card">
                            <span className="feature-icon">🖼️</span>
                            <h4>Image Search</h4>
                            <p>Visual semantic search with CLIP</p>
                        </div>
                        <div className="feature-card glass-card">
                            <span className="feature-icon">🎵</span>
                            <h4>Audio Search</h4>
                            <p>Speech-to-text with Whisper</p>
                        </div>
                    </div>
                </div>

                {/* Quick Actions */}
                <div className="quick-actions flex gap-md">
                    <button
                        className={`btn ${showUpload ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setShowUpload(!showUpload)}
                    >
                        {showUpload ? '🔍 Search' : '📤 Upload Files'}
                    </button>
                </div>

                {/* Main Content */}
                {showUpload ? (
                    <UploadManager onUploadComplete={handleUploadComplete} />
                ) : (
                    <>
                        <SearchInterface onResults={handleResults} />
                        {results && <ResultsDisplay results={results} />}
                    </>
                )}
            </div>
        </div>
    );
}

export default Home;
