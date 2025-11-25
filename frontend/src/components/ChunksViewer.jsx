import React, { useState, useMemo } from 'react';
import './ChunksViewer.css';

function ChunksViewer({ isOpen, onClose, document, chunks }) {
    const [searchQuery, setSearchQuery] = useState('');
    const [copiedIndex, setCopiedIndex] = useState(null);

    if (!isOpen) return null;

    const filteredChunks = useMemo(() => {
        if (!chunks) return [];
        if (!searchQuery) return chunks;
        return chunks.filter(chunk =>
            chunk.content.toLowerCase().includes(searchQuery.toLowerCase())
        );
    }, [chunks, searchQuery]);

    const handleCopy = (content, index) => {
        navigator.clipboard.writeText(content);
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
    };

    // Highlight text matches
    const highlightText = (text, query) => {
        if (!query) return text;
        const parts = text.split(new RegExp(`(${query})`, 'gi'));
        return parts.map((part, i) =>
            part.toLowerCase() === query.toLowerCase() ?
                <span key={i} className="highlight">{part}</span> : part
        );
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content chunks-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <div className="header-top">
                        <h3>Document Chunks</h3>
                        <button className="close-btn" onClick={onClose} title="Close">&times;</button>
                    </div>
                    <div className="modal-meta">
                        <span>{document?.original_filename}</span>
                        <span className="separator">•</span>
                        <span>{chunks?.length || 0} chunks</span>
                    </div>
                    <div className="chunks-search">
                        <span className="search-icon">🔍</span>
                        <input
                            type="text"
                            placeholder="Search within chunks..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            autoFocus
                        />
                        {searchQuery && (
                            <span className="match-count">
                                {filteredChunks.length} matches
                            </span>
                        )}
                    </div>
                </div>

                <div className="modal-body">
                    <div className="chunks-list">
                        {filteredChunks.length > 0 ? (
                            filteredChunks.map((chunk, index) => (
                                <div key={index} className="chunk-item glass-card">
                                    <div className="chunk-header">
                                        <div className="chunk-info">
                                            <span className="chunk-index">Chunk #{chunks.indexOf(chunk) + 1}</span>
                                            <span className="chunk-tokens">{chunk.token_count} tokens</span>
                                        </div>
                                        <button
                                            className={`copy-btn ${copiedIndex === index ? 'copied' : ''}`}
                                            onClick={() => handleCopy(chunk.content, index)}
                                            title="Copy content"
                                        >
                                            {copiedIndex === index ? '✓ Copied' : '📋 Copy'}
                                        </button>
                                    </div>
                                    <div className="chunk-content">
                                        {highlightText(chunk.content, searchQuery)}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="no-results">
                                <p>No chunks found matching "{searchQuery}"</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ChunksViewer;
