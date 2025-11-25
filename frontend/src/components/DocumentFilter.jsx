import { useState, useEffect } from 'react';
import './DocumentFilter.css';

function DocumentFilter({ selectedDocuments, onFilterChange }) {
    const [documents, setDocuments] = useState([]);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        // Fetch documents list
        fetch('/api/documents')
            .then(res => res.json())
            .then(data => setDocuments(data))
            .catch(err => console.error('Error loading documents:', err));
    }, []);

    const toggleDocument = (docId) => {
        const newSelection = selectedDocuments.includes(docId)
            ? selectedDocuments.filter(id => id !== docId)
            : [...selectedDocuments, docId];
        onFilterChange(newSelection);
    };

    const selectAll = () => {
        onFilterChange(documents.map(d => d.id));
    };

    const clearAll = () => {
        onFilterChange([]);
    };

    const getDocumentIcon = (fileType) => {
        if (fileType === 'pdf') return '📄';
        if (fileType === 'docx' || fileType === 'doc') return '📝';
        if (fileType === 'txt') return '📃';
        if (fileType === 'jpg' || fileType === 'png' || fileType === 'jpeg') return '🖼️';
        if (fileType === 'mp3' || fileType === 'wav') return '🎵';
        return '📁';
    };

    return (
        <div className="document-filter">
            <button
                className="filter-toggle btn-secondary"
                onClick={() => setIsOpen(!isOpen)}
            >
                <span className="toggle-label">
                    📁 Filter by Document
                    {selectedDocuments.length > 0 && (
                        <span className="filter-badge">{selectedDocuments.length}</span>
                    )}
                </span>
                <span className="arrow">{isOpen ? '▲' : '▼'}</span>
            </button>

            {isOpen && (
                <div className="filter-dropdown glass-card">
                    <div className="filter-header">
                        <h4>Select Documents</h4>
                        <div className="filter-actions">
                            <button className="btn-text" onClick={selectAll}>All</button>
                            <button className="btn-text" onClick={clearAll}>Clear</button>
                        </div>
                    </div>

                    <div className="filter-list">
                        {documents.length === 0 ? (
                            <div className="no-documents">No documents uploaded</div>
                        ) : (
                            documents.map(doc => (
                                <label key={doc.id} className="filter-item">
                                    <input
                                        type="checkbox"
                                        checked={selectedDocuments.includes(doc.id)}
                                        onChange={() => toggleDocument(doc.id)}
                                    />
                                    <span className="doc-icon">{getDocumentIcon(doc.file_type)}</span>
                                    <span className="doc-name">{doc.original_filename}</span>
                                </label>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default DocumentFilter;
