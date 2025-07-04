// src/App.js - Updated with CreateTable and GameSummary routes
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Login from './components/Login';
import Register from './components/Register';
import Profile from './components/Profile';
import TableList from './components/TableList';
import TableDetail from './components/TableDetail';
import CreateTable from './components/CreateTable';
import PokerTable from './components/PokerTable';
import GameSummary from './components/GameSummary';
import MatchHistory from './components/MatchHistory';
import PrivateRoute from './components/PrivateRoute';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar />
        
        <main className="main-content">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            <Route path="/profile" element={
              <PrivateRoute>
                <Profile />
              </PrivateRoute>
            } />
            
            <Route path="/history" element={
              <PrivateRoute>
                <MatchHistory />
              </PrivateRoute>
            } />
            
            <Route path="/tables" element={
              <PrivateRoute>
                <TableList />
              </PrivateRoute>
            } />
            
            <Route path="/tables/create" element={
              <PrivateRoute>
                <CreateTable />
              </PrivateRoute>
            } />
            
            <Route path="/tables/:id" element={
              <PrivateRoute>
                <TableDetail />
              </PrivateRoute>
            } />
            
            <Route path="/games/:id" element={
              <PrivateRoute>
                <PokerTable />
              </PrivateRoute>
            } />
            
            <Route path="/games/:gameId/summary" element={
              <PrivateRoute>
                <GameSummary />
              </PrivateRoute>
            } />
            
            <Route path="/" element={<Navigate to="/tables" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;