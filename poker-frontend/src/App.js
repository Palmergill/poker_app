// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import TableList from './components/TableList';
import TableDetail from './components/TableDetail';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <h1>Poker App</h1>
          <nav>
            <ul>
              <li>
                <Link to="/">Home</Link>
              </li>
              <li>
                <Link to="/tables">Tables</Link>
              </li>
            </ul>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<div>Welcome to the Poker App!</div>} />
            <Route path="/tables" element={<TableList />} />
            <Route path="/tables/:id" element={<TableDetail />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;