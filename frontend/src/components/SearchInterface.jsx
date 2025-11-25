import { useState } from 'react';
import { queryRAG } from '../api';
import './SearchInterface.css';
import SmartSuggestions from './SmartSuggestions';

function SearchInterface({ onResults, selectedDocuments = [], advancedFilters = null }) {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
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
            const requestBody = {
                question: query,
                top_k: 5
            };

            if (selectedDocuments.length > 0) {
                requestBody.document_ids = selectedDocuments;
            }

            if (advancedFilters) {
                requestBody.filters = advancedFilters;
            }

            const response = await queryRAG(requestBody);

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

    const handleVoiceInput = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            setIsRecording(true);
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            setQuery(transcript);
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            setIsRecording(false);
            if (event.error === 'no-speech') {
                alert('No speech detected. Please try again.');
            } else if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please allow microphone access.');
            }
        };

        recognition.onend = () => {
            setIsRecording(false);
        };

        recognition.start();
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
                        type="button"
                        className={`mic-button ${isRecording ? 'recording' : ''}`}
                        onClick={handleVoiceInput}
                        disabled={loading}
                        title={isRecording ? "Recording..." : "Click to speak"}
                    >
                        {isRecording ? (
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                <circle cx="12" cy="12" r="8" />
                            </svg>
                        ) : (
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                                <line x1="12" y1="19" x2="12" y2="23" />
                                <line x1="8" y1="23" x2="16" y2="23" />
                            </svg>
                        )}
                    </button>
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

                <SmartSuggestions onSuggestionClick={(question) => {
                    setQuery(question);
                    // Optional: auto-submit
                    // handleSubmit({ preventDefault: () => {} });
                }} />

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
