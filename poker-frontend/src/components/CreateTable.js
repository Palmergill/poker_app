// src/components/CreateTable.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { tableService } from '../services/apiService';

const CreateTable = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    max_players: 9,
    small_blind: '',
    big_blind: '',
    min_buy_in: '',
    max_buy_in: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Validate form inputs
    if (!formData.name.trim()) {
      setError('Table name is required');
      setLoading(false);
      return;
    }

    // Convert string values to numbers
    const tableData = {
      ...formData,
      small_blind: parseFloat(formData.small_blind),
      big_blind: parseFloat(formData.big_blind),
      min_buy_in: parseFloat(formData.min_buy_in),
      max_buy_in: parseFloat(formData.max_buy_in)
    };

    // Validate numeric values
    if (isNaN(tableData.small_blind) || tableData.small_blind <= 0) {
      setError('Small blind must be a positive number');
      setLoading(false);
      return;
    }

    if (isNaN(tableData.big_blind) || tableData.big_blind <= 0) {
      setError('Big blind must be a positive number');
      setLoading(false);
      return;
    }

    if (isNaN(tableData.min_buy_in) || tableData.min_buy_in <= 0) {
      setError('Minimum buy-in must be a positive number');
      setLoading(false);
      return;
    }

    if (isNaN(tableData.max_buy_in) || tableData.max_buy_in <= 0) {
      setError('Maximum buy-in must be a positive number');
      setLoading(false);
      return;
    }

    // Validate relationships between values
    if (tableData.big_blind < tableData.small_blind) {
      setError('Big blind must be greater than or equal to small blind');
      setLoading(false);
      return;
    }

    if (tableData.min_buy_in < tableData.big_blind * 10) {
      setError('Minimum buy-in should be at least 10 times the big blind');
      setLoading(false);
      return;
    }

    if (tableData.max_buy_in < tableData.min_buy_in) {
      setError('Maximum buy-in must be greater than or equal to minimum buy-in');
      setLoading(false);
      return;
    }

    try {
      const response = await tableService.createTable(tableData);
      // Navigate to the table detail page
      navigate(`/tables/${response.data.id}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create table');
      setLoading(false);
    }
  };

  return (
    <div className="create-table">
      <h2>Create New Poker Table</h2>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Table Name</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Maximum Players</label>
          <input
            type="number"
            name="max_players"
            min="2"
            max="10"
            value={formData.max_players}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Small Blind ($)</label>
          <input
            type="number"
            name="small_blind"
            min="0.01"
            step="0.01"
            value={formData.small_blind}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Big Blind ($)</label>
          <input
            type="number"
            name="big_blind"
            min="0.02"
            step="0.01"
            value={formData.big_blind}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Minimum Buy-in ($)</label>
          <input
            type="number"
            name="min_buy_in"
            min="1"
            step="0.01"
            value={formData.min_buy_in}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Maximum Buy-in ($)</label>
          <input
            type="number"
            name="max_buy_in"
            min="1"
            step="0.01"
            value={formData.max_buy_in}
            onChange={handleChange}
            required
          />
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Creating...' : 'Create Table'}
        </button>
      </form>
    </div>
  );
};

export default CreateTable;