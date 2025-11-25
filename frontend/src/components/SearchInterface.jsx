import { useState } from 'react';
import { queryRAG } from '../api';
import './SearchInterface.css';

function SearchInterface({ onResults }) {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [modalities, setModalities] = useState({
        text: true,
        image: true,
        audio: true,
    });

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!query.trim()) return;

        setLoading(true);

        try {
            const selectedModalities = Object.keys(modalities).filter(m => modalities[m]);
            const response = await queryRAG(query, 5, selectedModalities);

            if (onResults) {
                onResults(response.data);
            }
        } catch (error) {
            console.error('Search error:', error);
            alert('Error performing search. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const toggleModality = (modality) => {
        setModalities(prev => ({
            ...prev,
            [modality]: !prev[modality]
        }));
    };

    return (
        <div className="search-interface glass-card">
            <form onSubmit={handleSubmit} className="search-form">
                <div className="search-input-wrapper">
                    <input
                        type="text"
                        className="search-input input"
                        placeholder="Ask a question or search across your documents..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        className="search-button btn btn-primary"
                        disabled={loading || !query.trim()}
                    >
                        {loading ? (
                            <>
                                <span className="spinner" style={{ width: '20px', height: '20px' }}></span>
                                Searching...
                            </>
                        ) : (
                            <>
                                <span>🔍</span>
                                Search
                            </>
                        )}
                    </button>
                </div>

                <div className="modality-filters">
                    <span className="filter-label">Search in:</span>
                    <div className="filter-options flex gap-md">
                        <label className={`filter-option ${modalities.text ? 'active' : ''}`}>
                            <input
                                type="checkbox"
                                checked={modalities.text}
                                onChange={() => toggleModality('text')}
                            />
                            <span className="filter-icon">📄</span>
                            <span>Documents</span>
                        </label>

                        <label className={`filter-option ${modalities.image ? 'active' : ''}`}>
                            <input
                                type="checkbox"
                                checked={modalities.image}
                                onChange={() => toggleModality('image')}
                            />
                            <span className="filter-icon">🖼️</span>
                            <span>Images</span>
                        </label>

                        <label className={`filter-option ${modalities.audio ? 'active' : ''}`}>
                            <input
                                type="checkbox"
                                checked={modalities.audio}
                                onChange={() => toggleModality('audio')}
                            />
                            <span className="filter-icon">🎵</span>
                            <span>Audio</span>
                        </label>
                    </div>
                </div>
            </form>
        </div>
    );
}

export default SearchInterface;
