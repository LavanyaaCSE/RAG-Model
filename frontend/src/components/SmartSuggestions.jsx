import { useState, useEffect } from 'react';
import api from '../api';
import './SmartSuggestions.css';

function SmartSuggestions({ onSuggestionClick }) {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(false);

    const fetchSuggestions = async () => {
        setLoading(true);
        try {
            const response = await api.get('/suggestions');
            if (Array.isArray(response.data)) {
                setSuggestions(response.data);
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSuggestions();
    }, []);

    if (suggestions.length === 0 && !loading) return null;

    return (
        <div className="smart-suggestions">
            <div className="suggestions-header">
                <span className="sparkle-icon">✨</span>
                <span className="suggestions-title">Smart Suggestions</span>
                <button
                    className="refresh-btn"
                    onClick={fetchSuggestions}
                    disabled={loading}
                    title="Get new suggestions"
                >
                    {loading ? '🔄' : '↻'}
                </button>
            </div>
            <div className="suggestions-list">
                {suggestions.map((question, index) => (
                    <button
                        key={index}
                        className="suggestion-chip"
                        onClick={() => onSuggestionClick(question)}
                    >
                        {question}
                    </button>
                ))}
            </div>
        </div>
    );
}

export default SmartSuggestions;
