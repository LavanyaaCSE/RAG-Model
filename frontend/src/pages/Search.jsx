import { useState } from 'react';
import SearchInterface from '../components/SearchInterface';
import ResultsDisplay from '../components/ResultsDisplay';
import DocumentFilter from '../components/DocumentFilter';
import AdvancedFilters from '../components/AdvancedFilters';
import SimilaritySearch from '../components/SimilaritySearch';
import ImageSearch from '../components/ImageSearch';
import './Search.css';

function Search() {
    const [results, setResults] = useState(null);
    const [selectedDocuments, setSelectedDocuments] = useState([]);
    const [advancedFilters, setAdvancedFilters] = useState(null);
    const [searchMode, setSearchMode] = useState('text'); // 'text', 'similarity', or 'image'

    const handleResults = (data) => {
        setResults(data);
    };

    const handleFilterChange = (docIds) => {
        setSelectedDocuments(docIds);
        setResults(null);
    };

    const handleAdvancedFilterChange = (filters) => {
        setAdvancedFilters(filters);
        setResults(null); // Clear results when filters change
    };

    return (
        <div className="search-page">
            <div className="container">
                <div className="page-header">
                    <h2>Advanced Search</h2>
                    <p>Search across all your documents</p>
                </div>

                <div className="search-mode-toggle">
                    <button
                        className={`mode-btn ${searchMode === 'text' ? 'active' : ''}`}
                        onClick={() => setSearchMode('text')}
                    >
                        💬 Text Query
                    </button>
                    <button
                        className={`mode-btn ${searchMode === 'similarity' ? 'active' : ''}`}
                        onClick={() => setSearchMode('similarity')}
                    >
                        📤 Find Similar
                    </button>
                    <button
                        className={`mode-btn ${searchMode === 'image' ? 'active' : ''}`}
                        onClick={() => setSearchMode('image')}
                    >
                        🖼️ Image Search
                    </button>
                </div>

                {searchMode === 'text' ? (
                    <>
                        <div className="filters-row">
                            <DocumentFilter
                                selectedDocuments={selectedDocuments}
                                onFilterChange={handleFilterChange}
                            />
                            <AdvancedFilters onFilterChange={handleAdvancedFilterChange} />
                        </div>

                        <SearchInterface
                            onResults={handleResults}
                            selectedDocuments={selectedDocuments}
                            advancedFilters={advancedFilters}
                        />

                        {results && <ResultsDisplay results={results} />}

                        {!results && (
                            <div className="search-placeholder glass-card">
                                <span className="placeholder-icon">🔍</span>
                                <h3>Start Searching</h3>
                                <p>
                                    {selectedDocuments.length > 0
                                        ? `Searching in ${selectedDocuments.length} selected document(s)`
                                        : 'Enter a question or search query above to find relevant content'
                                    }
                                </p>
                            </div>
                        )}
                    </>
                ) : searchMode === 'similarity' ? (
                    <SimilaritySearch advancedFilters={advancedFilters} />
                ) : (
                    <ImageSearch advancedFilters={advancedFilters} />
                )}
            </div>
        </div>
    );
}

export default Search;
