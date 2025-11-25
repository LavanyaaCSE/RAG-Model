import { useState } from 'react';
import { uploadDocument, uploadImage, uploadAudio } from '../api';
import './UploadManager.css';

function UploadManager({ onUploadComplete }) {
    const [files, setFiles] = useState([]);
    const [uploading, setUploading] = useState(false);
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

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFiles(Array.from(e.dataTransfer.files));
        }
    };

    const handleFileInput = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFiles(Array.from(e.target.files));
        }
    };

    const handleFiles = (newFiles) => {
        const fileObjects = newFiles.map(file => ({
            file,
            name: file.name,
            size: file.size,
            type: getFileType(file),
            progress: 0,
            status: 'pending', // pending, uploading, completed, error
            id: Math.random().toString(36).substr(2, 9)
        }));

        setFiles(prev => [...prev, ...fileObjects]);
    };

    const getFileType = (file) => {
        const ext = file.name.split('.').pop().toLowerCase();
        if (['pdf', 'docx', 'doc'].includes(ext)) return 'document';
        if (['png', 'jpg', 'jpeg', 'gif', 'bmp'].includes(ext)) return 'image';
        if (['mp3', 'wav', 'm4a', 'flac', 'ogg'].includes(ext)) return 'audio';
        return 'unknown';
    };

    const uploadFile = async (fileObj) => {
        const { file, type, id } = fileObj;

        // Update status
        setFiles(prev => prev.map(f =>
            f.id === id ? { ...f, status: 'uploading' } : f
        ));

        try {
            let uploadFn;
            if (type === 'document') uploadFn = uploadDocument;
            else if (type === 'image') uploadFn = uploadImage;
            else if (type === 'audio') uploadFn = uploadAudio;
            else throw new Error('Unsupported file type');

            await uploadFn(file, (progress) => {
                setFiles(prev => prev.map(f =>
                    f.id === id ? { ...f, progress } : f
                ));
            });

            setFiles(prev => prev.map(f =>
                f.id === id ? { ...f, status: 'completed', progress: 100 } : f
            ));

            if (onUploadComplete) {
                onUploadComplete();
            }
        } catch (error) {
            console.error('Upload error:', error);
            setFiles(prev => prev.map(f =>
                f.id === id ? { ...f, status: 'error' } : f
            ));
        }
    };

    const handleUploadAll = async () => {
        setUploading(true);
        const pendingFiles = files.filter(f => f.status === 'pending');

        for (const fileObj of pendingFiles) {
            await uploadFile(fileObj);
        }

        setUploading(false);
    };

    const removeFile = (id) => {
        setFiles(prev => prev.filter(f => f.id !== id));
    };

    const clearCompleted = () => {
        setFiles(prev => prev.filter(f => f.status !== 'completed'));
    };

    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    return (
        <div className="upload-manager glass-card">
            <h3>Upload Files</h3>

            <div
                className={`upload-dropzone ${dragActive ? 'active' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                <div className="dropzone-content">
                    <span className="dropzone-icon">📁</span>
                    <p className="dropzone-text">
                        Drag and drop files here, or click to select
                    </p>
                    <p className="dropzone-hint">
                        Supports PDF, DOCX, Images, and Audio files
                    </p>
                    <input
                        type="file"
                        multiple
                        onChange={handleFileInput}
                        className="file-input"
                        accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.gif,.bmp,.mp3,.wav,.m4a,.flac,.ogg"
                    />
                </div>
            </div>

            {files.length > 0 && (
                <>
                    <div className="files-list">
                        {files.map(fileObj => (
                            <div key={fileObj.id} className="file-item">
                                <div className="file-info">
                                    <span className="file-icon">
                                        {fileObj.type === 'document' && '📄'}
                                        {fileObj.type === 'image' && '🖼️'}
                                        {fileObj.type === 'audio' && '🎵'}
                                    </span>
                                    <div className="file-details">
                                        <div className="file-name">{fileObj.name}</div>
                                        <div className="file-meta">
                                            {formatFileSize(fileObj.size)}
                                            {fileObj.status === 'uploading' && ` • ${fileObj.progress}%`}
                                        </div>
                                    </div>
                                </div>

                                <div className="file-actions">
                                    {fileObj.status === 'completed' && (
                                        <span className="badge badge-success">✓ Done</span>
                                    )}
                                    {fileObj.status === 'error' && (
                                        <span className="badge badge-error">✗ Error</span>
                                    )}
                                    {fileObj.status === 'uploading' && (
                                        <div className="progress-bar">
                                            <div
                                                className="progress-fill"
                                                style={{ width: `${fileObj.progress}%` }}
                                            />
                                        </div>
                                    )}
                                    {fileObj.status === 'pending' && (
                                        <button
                                            className="btn btn-ghost"
                                            onClick={() => removeFile(fileObj.id)}
                                        >
                                            ✕
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="upload-actions flex justify-between">
                        <button
                            className="btn btn-secondary"
                            onClick={clearCompleted}
                            disabled={!files.some(f => f.status === 'completed')}
                        >
                            Clear Completed
                        </button>
                        <button
                            className="btn btn-primary"
                            onClick={handleUploadAll}
                            disabled={uploading || !files.some(f => f.status === 'pending')}
                        >
                            {uploading ? 'Uploading...' : `Upload ${files.filter(f => f.status === 'pending').length} Files`}
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}

export default UploadManager;
