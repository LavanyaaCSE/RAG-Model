import { useState } from 'react';
import SearchInterface from '../components/SearchInterface';
import ResultsDisplay from '../components/ResultsDisplay';
import './Search.css';

function Search() {
    const [results, setResults] = useState(null);

    const handleResults = (data) => {
        setResults(data);
    };

    return (
        <div className="search-page">
            <div className="container">
                <div className="page-header">
                    <h2>Advanced Search</h2>
                    <p>Search across all your documents, images, and audio files</p>
                </div>

                <SearchInterface onResults={handleResults} />

                {results && <ResultsDisplay results={results} />}

                {!results && (
                    <div className="search-placeholder glass-card">
                        <span className="placeholder-icon">🔍</span>
                        <h3>Start Searching</h3>
                        <p>Enter a question or search query above to find relevant content across all your uploaded files.</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default Search;
