import { useState, useEffect } from 'react';
import './AdvancedFilters.css';

function AdvancedFilters({ onFilterChange }) {
    const [filters, setFilters] = useState({
        startDate: '',
        endDate: '',
        minSize: '',
        maxSize: ''
    });

    const [isOpen, setIsOpen] = useState(false);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFilters(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleApply = () => {
        onFilterChange(filters);
    };

    const handleReset = () => {
        const emptyFilters = {
            startDate: '',
            endDate: '',
            minSize: '',
            maxSize: ''
        };
        setFilters(emptyFilters);
        onFilterChange(emptyFilters);
    };

    return (
        <div className="advanced-filters-container">
            <button
                className={`btn-filter-toggle ${isOpen ? 'active' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
            >
                <span>⚡ Advanced Filters</span>
                <span className="arrow">{isOpen ? '▲' : '▼'}</span>
            </button>

            {isOpen && (
                <div className="advanced-filters-panel glass-card">
                    <div className="filter-group">
                        <label>Date Range</label>
                        <div className="filter-row">
                            <div className="input-wrapper">
                                <span className="input-label">From</span>
                                <input
                                    type="date"
                                    name="startDate"
                                    value={filters.startDate}
                                    onChange={handleChange}
                                    className="filter-input"
                                />
                            </div>
                            <div className="input-wrapper">
                                <span className="input-label">To</span>
                                <input
                                    type="date"
                                    name="endDate"
                                    value={filters.endDate}
                                    onChange={handleChange}
                                    className="filter-input"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="filter-group">
                        <label>File Size (MB)</label>
                        <div className="filter-row">
                            <div className="input-wrapper">
                                <span className="input-label">Min</span>
                                <input
                                    type="number"
                                    name="minSize"
                                    value={filters.minSize}
                                    onChange={handleChange}
                                    placeholder="0"
                                    min="0"
                                    className="filter-input"
                                />
                            </div>
                            <div className="input-wrapper">
                                <span className="input-label">Max</span>
                                <input
                                    type="number"
                                    name="maxSize"
                                    value={filters.maxSize}
                                    onChange={handleChange}
                                    placeholder="Any"
                                    min="0"
                                    className="filter-input"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="filter-actions">
                        <button className="btn-reset" onClick={handleReset}>
                            Reset
                        </button>
                        <button className="btn-apply" onClick={handleApply}>
                            Apply Filters
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default AdvancedFilters;
