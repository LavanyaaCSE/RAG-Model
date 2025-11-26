import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import Search from './pages/Search';
import Documents from './pages/Documents';
import './App.css';

function App() {
    return (
        <Router>
            <div className="app">
                import Navbar from './components/Navbar';

                function App() {
    return (
                <Router>
                    <div className="app">
                        <Navbar />

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
