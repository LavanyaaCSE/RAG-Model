import './CitationPanel.css';

function CitationPanel({ citation, onClose }) {
    if (!citation) return null;

    return (
        <div className="citation-panel-overlay" onClick={onClose}>
            <div className="citation-panel glass-card" onClick={(e) => e.stopPropagation()}>
                <div className="panel-header">
                    <h3>Citation Details [{citation.id}]</h3>
                    <button className="close-button btn btn-ghost" onClick={onClose}>
                        ✕
                    </button>
                </div>

                <div className="panel-content">
                    <div className="citation-detail">
                        <label>Type</label>
                        <div className="detail-value">
                            {citation.type === 'text' && '📄 Document'}
                            {citation.type === 'image' && '🖼️ Image'}
                            {citation.type === 'audio' && '🎵 Audio'}
                        </div>
                    </div>

                    <div className="citation-detail">
                        <label>Source</label>
                        <div className="detail-value">{citation.source}</div>
                    </div>

                    {citation.page && (
                        <div className="citation-detail">
                            <label>Page</label>
                            <div className="detail-value">Page {citation.page}</div>
                        </div>
                    )}

                    {citation.start_time !== undefined && (
                        <div className="citation-detail">
                            <label>Timestamp</label>
                            <div className="detail-value">
                                {citation.start_time.toFixed(1)}s - {citation.end_time.toFixed(1)}s
                            </div>
                        </div>
                    )}

                    {citation.url && citation.type === 'image' && (
                        <div className="citation-detail">
                            <label>Preview</label>
                            <div className="image-preview">
                                <img src={citation.url} alt={citation.source} />
                            </div>
                        </div>
                    )}
                </div>

                <div className="panel-footer">
                    <button className="btn btn-secondary" onClick={onClose}>
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}

export default CitationPanel;
