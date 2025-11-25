import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import Search from './pages/Search';
import Documents from './pages/Documents';
import './App.css';

function App() {
    return (
        <Router>
            <div className="app">
                <nav className="navbar">
                    <div className="container flex items-center justify-between">
                        <Link to="/" className="logo">
                            <span className="logo-icon">🔍</span>
                            <span className="logo-text">Multimodal RAG</span>
                        </Link>

                        <div className="nav-links flex items-center gap-md">
                            <Link to="/" className="nav-link">Home</Link>
                            <Link to="/search" className="nav-link">Search</Link>
                            <Link to="/documents" className="nav-link">Documents</Link>
                        </div>
                    </div>
                </nav>

                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/search" element={<Search />} />
                        <Route path="/documents" element={<Documents />} />
                    </Routes>
                </main>

                <footer className="footer">
                    <div className="container">
                        <p className="footer-text">
                            Multimodal RAG System - Offline AI-Powered Search
                        </p>
                    </div>
                </footer>
            </div>
        </Router>
    );
}

export default App;
