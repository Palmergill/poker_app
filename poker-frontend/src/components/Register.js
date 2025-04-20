// src/components/Register.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validate passwords match
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      await axios.post('http://localhost:8000/api/register/', {
        username,
        email,
        password
      });
      
      // Redirect to login page
      navigate('/login');
    } catch (err) {
      if (err.response && err.response.data) {
        // Format error messages from API
        const errorMessages = [];
        for (const field in err.response.data) {
          errorMessages.push(`${field}: ${err.response.data[field].join(' ')}`);
        }
        setError(errorMessages.join('\n'));
      } else {
        setError('Registration failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-form">
      <h2>Register for Poker App</h2>
      {error && <div className="error-message">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Confirm Password</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Registering...' : 'Register'}
        </button>
      </form>
      
      <p>
        Already have an account? <a href="/login">Login</a>
      </p>
    </div>
  );
};

export default Register;

// src/components/Profile.js
import React, { useState, useEffect } from 'react';
import { playerService } from '../services/apiService';

const Profile = () => {
  const [profile, setProfile] = useState(null);
  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await playerService.getProfile();
      setProfile(response.data);
      setLoading(false);
    } catch (err) {
      setError('Failed to load profile');
      setLoading(false);
    }
  };

  const handleDeposit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    
    if (!depositAmount || parseFloat(depositAmount) <= 0) {
      setError('Please enter a valid deposit amount');
      return;
    }
    
    try {
      await playerService.deposit(depositAmount);
      setMessage(`Successfully deposited $${depositAmount}`);
      setDepositAmount('');
      fetchProfile(); // Refresh profile
    } catch (err) {
      setError('Failed to process deposit');
    }
  };

  const handleWithdraw = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    
    if (!withdrawAmount || parseFloat(withdrawAmount) <= 0) {
      setError('Please enter a valid withdrawal amount');
      return;
    }
    
    try {
      await playerService.withdraw(withdrawAmount);
      setMessage(`Successfully withdrew $${withdrawAmount}`);
      setWithdrawAmount('');
      fetchProfile(); // Refresh profile
    } catch (err) {
      setError('Failed to process withdrawal');
    }
  };

  if (loading) {
    return <div className="loading">Loading profile...</div>;
  }

  return (
    <div className="profile">
      <h2>Player Profile</h2>
      
      {error && <div className="error-message">{error}</div>}
      {message && <div className="success-message">{message}</div>}
      
      {profile && (
        <div className="profile-details">
          <p><strong>Username:</strong> {profile.user.username}</p>
          <p><strong>Email:</strong> {profile.user.email}</p>
          <p><strong>Current Balance:</strong> ${profile.balance}</p>
          
          <div className="balance-actions">
            <div className="action-card">
              <h3>Deposit Funds</h3>
              <form onSubmit={handleDeposit}>
                <div className="form-group">
                  <label>Amount</label>
                  <input
                    type="number"
                    min="1"
                    step="0.01"
                    value={depositAmount}
                    onChange={(e) => setDepositAmount(e.target.value)}
                    required
                  />
                </div>
                <button type="submit">Deposit</button>
              </form>
            </div>
            
            <div className="action-card">
              <h3>Withdraw Funds</h3>
              <form onSubmit={handleWithdraw}>
                <div className="form-group">
                  <label>Amount</label>
                  <input
                    type="number"
                    min="1"
                    max={profile.balance}
                    step="0.01"
                    value={withdrawAmount}
                    onChange={(e) => setWithdrawAmount(e.target.value)}
                    required
                  />
                </div>
                <button type="submit">Withdraw</button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;