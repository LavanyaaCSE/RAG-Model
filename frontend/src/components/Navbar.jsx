import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

function Navbar() {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const location = useLocation();

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const closeMenu = () => {
        setIsMenuOpen(false);
    };

    const isActive = (path) => {
        return location.pathname === path ? 'active' : '';
    };

    return (
        <nav className="navbar">
            <div className="container navbar-container">
                <Link to="/" className="logo" onClick={closeMenu}>
                    <span className="logo-icon">🔍</span>
                    <span className="logo-text">Multimodal RAG</span>
                </Link>

                <button
                    className={`mobile-menu-btn ${isMenuOpen ? 'open' : ''}`}
                    onClick={toggleMenu}
                    aria-label="Toggle menu"
                >
                    <span></span>
                    <span></span>
                    <span></span>
                </button>

                <div className={`nav-links ${isMenuOpen ? 'active' : ''}`}>
                    <Link
                        to="/"
                        className={`nav-link ${isActive('/')}`}
                        onClick={closeMenu}
                    >
                        Home
                    </Link>
                    <Link
                        to="/search"
                        className={`nav-link ${isActive('/search')}`}
                        onClick={closeMenu}
                    >
                        Search
                    </Link>
                    <Link
                        to="/documents"
                        className={`nav-link ${isActive('/documents')}`}
                        onClick={closeMenu}
                    >
                        Documents
                    </Link>
                </div>
            </div>
        </nav>
    );
}

export default Navbar;
