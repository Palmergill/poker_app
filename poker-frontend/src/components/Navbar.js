// src/components/Navbar.js
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authService } from '../services/apiService';

const Navbar = () => {
  const navigate = useNavigate();
  const isAuthenticated = authService.isAuthenticated();
  const user = isAuthenticated ? JSON.parse(localStorage.getItem('user')) : null;

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">Poker App</Link>
      </div>
      
      <div className="navbar-menu">
        {isAuthenticated ? (
          <>
            <Link to="/tables" className="nav-item">Tables</Link>
            <Link to="/profile" className="nav-item">Profile</Link>
            <span className="nav-item username">Hello, {user ? user.username : 'Player'}</span>
            <button onClick={handleLogout} className="nav-item logout-btn">Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" className="nav-item">Login</Link>
            <Link to="/register" className="nav-item">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
