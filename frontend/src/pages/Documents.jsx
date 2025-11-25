import { useState, useEffect } from 'react';
import { getDocuments, deleteDocument, getDownloadUrl, getDocumentChunks } from '../api';
import UploadManager from '../components/UploadManager';
import ChunksViewer from '../components/ChunksViewer';
import './Documents.css';

function Documents() {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');
    const [showUpload, setShowUpload] = useState(false);

    // Chunks viewer state
    const [selectedDoc, setSelectedDoc] = useState(null);
    const [docChunks, setDocChunks] = useState([]);
    const [showChunks, setShowChunks] = useState(false);

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const response = await getDocuments(0, 100, filter === 'all' ? null : filter);
            setDocuments(response.data);
        } catch (error) {
            console.error('Error fetching documents:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, [filter]);

    const handleDelete = async (id) => {
        if (!confirm('Are you sure you want to delete this document?')) return;

        try {
            await deleteDocument(id);
            fetchDocuments();
        } catch (error) {
            console.error('Error deleting document:', error);
            alert('Error deleting document');
        }
    };

    const handleOpen = async (id) => {
        try {
            const response = await getDownloadUrl(id);
            window.open(response.data.url, '_blank');
        } catch (error) {
            console.error('Error opening document:', error);
            alert('Error opening document');
        }
    };

    const handleViewChunks = async (doc) => {
        try {
            const response = await getDocumentChunks(doc.id);
            setDocChunks(response.data);
            setSelectedDoc(doc);
            setShowChunks(true);
        } catch (error) {
            console.error('Error fetching chunks:', error);
            alert('Error fetching document chunks');
        }
    };

    const getStatusBadge = (status) => {
        switch (status) {
            case 0: return <span className="badge badge-warning">Pending</span>;
            case 1: return <span className="badge badge-info">Processing</span>;
            case 2: return <span className="badge badge-success">Completed</span>;
            case 3: return <span className="badge badge-error">Failed</span>;
            default: return null;
        }
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'Just now';
        try {
            return new Date(dateString).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return 'Just now';
        }
    };

    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    return (
        <div className="documents-page">
            <div className="container">
                <div className="page-header">
                    <h2>My Documents</h2>
                    <button
                        className="btn btn-primary"
                        onClick={() => setShowUpload(!showUpload)}
                    >
                        {showUpload ? '📋 View Documents' : '📤 Upload Files'}
                    </button>
                </div>

                {showUpload ? (
                    <UploadManager onUploadComplete={() => {
                        setShowUpload(false);
                        fetchDocuments();
                    }} />
                ) : (
                    <>
                        <div className="documents-filters flex gap-md">
                            <button
                                className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => setFilter('all')}
                            >
                                All
                            </button>
                            <button
                                className={`btn ${filter === 'text' ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => setFilter('text')}
                            >
                                📄 Documents
                            </button>
                            <button
                                className={`btn ${filter === 'image' ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => setFilter('image')}
                            >
                                🖼️ Images
                            </button>
                            <button
                                className={`btn ${filter === 'audio' ? 'btn-primary' : 'btn-secondary'}`}
                                onClick={() => setFilter('audio')}
                            >
                                🎵 Audio
                            </button>
                        </div>

                        {loading ? (
                            <div className="loading-state">
                                <div className="spinner"></div>
                                <p>Loading documents...</p>
                            </div>
                        ) : documents.length === 0 ? (
                            <div className="empty-state glass-card">
                                <span className="empty-icon">📂</span>
                                <h3>No Documents Yet</h3>
                                <p>Upload your first document to get started</p>
                                <button
                                    className="btn btn-primary"
                                    onClick={() => setShowUpload(true)}
                                >
                                    Upload Files
                                </button>
                            </div>
                        ) : (
                            <div className="documents-grid">
                                {documents.map((doc) => (
                                    <div key={doc.id} className="document-card glass-card">
                                        <div className="document-icon">
                                            {doc.modality === 'text' && '📄'}
                                            {doc.modality === 'image' && '🖼️'}
                                            {doc.modality === 'audio' && '🎵'}
                                        </div>

                                        <div className="document-info">
                                            <h4 className="document-name">{doc.original_filename}</h4>
                                            <div className="document-meta">
                                                <span>{formatFileSize(doc.file_size)}</span>
                                                <span>•</span>
                                                <span>{formatDate(doc.upload_date)}</span>
                                                {doc.chunk_count && (
                                                    <>
                                                        <span>•</span>
                                                        <span
                                                            className="chunk-count-link"
                                                            onClick={() => handleViewChunks(doc)}
                                                            title="View chunks"
                                                        >
                                                            {doc.chunk_count} chunks
                                                        </span>
                                                    </>
                                                )}
                                            </div>
                                            <div className="document-status">
                                                {getStatusBadge(doc.processed)}
                                            </div>
                                        </div>

                                        <div className="document-actions">
                                            <button
                                                className="btn btn-ghost"
                                                onClick={() => handleOpen(doc.id)}
                                                title="Open file"
                                            >
                                                📂
                                            </button>
                                            <button
                                                className="btn btn-ghost"
                                                onClick={() => handleViewChunks(doc)}
                                                title="View Chunks"
                                            >
                                                🧩
                                            </button>
                                            <button
                                                className="btn btn-ghost"
                                                onClick={() => handleDelete(doc.id)}
                                                title="Delete"
                                            >
                                                🗑️
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </div>

            <ChunksViewer
                isOpen={showChunks}
                onClose={() => setShowChunks(false)}
                document={selectedDoc}
                chunks={docChunks}
            />
        </div>
    );
}

export default Documents;
