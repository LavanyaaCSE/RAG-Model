import { useState } from 'react';
import CitationPanel from './CitationPanel';
import './ResultsDisplay.css';

function ResultsDisplay({ results }) {
    const [selectedCitation, setSelectedCitation] = useState(null);

    if (!results) {
        return null;
    }

    const { answer, citations, context_used } = results;

    // Parse citations in answer text
    const renderAnswerWithCitations = (text) => {
        const citationRegex = /\[(\d+)\]/g;
        const parts = [];
        let lastIndex = 0;
        let match;

        while ((match = citationRegex.exec(text)) !== null) {
            // Add text before citation
            if (match.index > lastIndex) {
                parts.push(
                    <span key={`text-${lastIndex}`}>
                        {text.substring(lastIndex, match.index)}
                    </span>
                );
            }

            // Add citation link
            const citationNum = parseInt(match[1]);
            const citation = citations.find(c => c.id === citationNum);

            parts.push(
                <button
                    key={`citation-${citationNum}`}
                    className="citation-link"
                    onClick={() => setSelectedCitation(citation)}
                    title={citation ? `View source: ${citation.source}` : ''}
                >
                    [{citationNum}]
                </button>
            );

            lastIndex = match.index + match[0].length;
        }

        // Add remaining text
        if (lastIndex < text.length) {
            parts.push(
                <span key={`text-${lastIndex}`}>
                    {text.substring(lastIndex)}
                </span>
            );
        }

        return parts;
    };

    return (
        <div className="results-display">
            <div className="answer-section glass-card animate-fade-in">
                <div className="answer-header">
                    <h3>Answer</h3>
                    <div className="context-badges flex gap-sm">
                        {context_used.text_chunks > 0 && (
                            <span className="badge badge-info">
                                📄 {context_used.text_chunks} docs
                            </span>
                        )}
                        {context_used.images > 0 && (
                            <span className="badge badge-info">
                                🖼️ {context_used.images} images
                            </span>
                        )}
                        {context_used.audio_segments > 0 && (
                            <span className="badge badge-info">
                                🎵 {context_used.audio_segments} audio
                            </span>
                        )}
                    </div>
                </div>

                <div className="answer-content">
                    <p>{renderAnswerWithCitations(answer)}</p>
                </div>
            </div>

            {citations && citations.length > 0 && (
                <div className="citations-section">
                    <h4 className="citations-header">Sources ({citations.length})</h4>
                    <div className="citations-grid">
                        {citations.map((citation) => (
                            <div
                                key={citation.id}
                                className="citation-card glass-card"
                                onClick={() => setSelectedCitation(citation)}
                            >
                                <div className="citation-number">[{citation.id}]</div>
                                <div className="citation-info">
                                    <div className="citation-type">
                                        {citation.type === 'text' && '📄'}
                                        {citation.type === 'image' && '🖼️'}
                                        {citation.type === 'audio' && '🎵'}
                                        <span className="badge badge-info">{citation.type}</span>
                                    </div>
                                    <div className="citation-source">{citation.source}</div>
                                    {citation.page && (
                                        <div className="citation-meta">Page {citation.page}</div>
                                    )}
                                    {citation.start_time !== undefined && (
                                        <div className="citation-meta">
                                            {citation.start_time.toFixed(1)}s - {citation.end_time.toFixed(1)}s
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {selectedCitation && (
                <CitationPanel
                    citation={selectedCitation}
                    onClose={() => setSelectedCitation(null)}
                />
            )}
        </div>
    );
}

export default ResultsDisplay;
