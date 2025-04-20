// src/components/TableDetail.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { tableService, playerService } from '../services/apiService';

const TableDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [table, setTable] = useState(null);
  const [player, setPlayer] = useState(null);
  const [buyIn, setBuyIn] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTableAndPlayer = async () => {
      try {
        const [tableResponse, playerResponse] = await Promise.all([
          tableService.getTable(id),
          playerService.getProfile()
        ]);
        
        setTable(tableResponse.data);
        setPlayer(playerResponse.data);
        
        // Set default buy-in to min buy-in
        setBuyIn(tableResponse.data.min_buy_in);
        
        setLoading(false);
      } catch (err) {
        setError('Failed to load table information');
        setLoading(false);
      }
    };

    fetchTableAndPlayer();
  }, [id]);

  const handleJoinTable = async () => {
    if (!buyIn || parseFloat(buyIn) < parseFloat(table.min_buy_in) || parseFloat(buyIn) > parseFloat(table.max_buy_in)) {
      setError(`Buy-in must be between $${table.min_buy_in} and $${table.max_buy_in}`);
      return;
    }

    if (parseFloat(buyIn) > parseFloat(player.balance)) {
      setError('Insufficient balance');
      return;
    }

    try {
      const response = await tableService.joinTable(id, buyIn);
      // Navigate to the game page
      navigate(`/games/${response.data.id}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to join table');
    }
  };

  if (loading) {
    return <div className="loading">Loading table details...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!table) {
    return <div className="error">Table not found</div>;
  }

  return (
    <div className="table-detail">
      <h2>{table.name}</h2>
      
      <div className="table-info-card">
        <h3>Table Information</h3>
        <div className="table-specs">
          <div className="spec-item">
            <span className="label">Small Blind:</span>
            <span className="value">${table.small_blind}</span>
          </div>
          
          <div className="spec-item">
            <span className="label">Big Blind:</span>
            <span className="value">${table.big_blind}</span>
          </div>
          
          <div className="spec-item">
            <span className="label">Min Buy-in:</span>
            <span className="value">${table.min_buy_in}</span>
          </div>
          
          <div className="spec-item">
            <span className="label">Max Buy-in:</span>
            <span className="value">${table.max_buy_in}</span>
          </div>
          
          <div className="spec-item">
            <span className="label">Max Players:</span>
            <span className="value">{table.max_players}</span>
          </div>
        </div>
      </div>
      
      {player && (
        <div className="join-table-section">
          <h3>Join This Table</h3>
          <p>Your current balance: ${player.balance}</p>
          
          <div className="buy-in-controls">
            <div className="form-group">
              <label>Buy-in Amount:</label>
              <input
                type="number"
                min={table.min_buy_in}
                max={Math.min(table.max_buy_in, player.balance)}
                step="0.01"
                value={buyIn}
                onChange={(e) => setBuyIn(e.target.value)}
              />
            </div>
            
            <button 
              onClick={handleJoinTable}
              disabled={!buyIn || parseFloat(buyIn) < parseFloat(table.min_buy_in) || 
                        parseFloat(buyIn) > parseFloat(table.max_buy_in) || 
                        parseFloat(buyIn) > parseFloat(player.balance)}
            >
              Join Table
            </button>
          </div>
          
          {parseFloat(player.balance) < parseFloat(table.min_buy_in) && (
            <div className="insufficient-funds">
              <p>You don't have enough funds to join this table.</p>
              <button onClick={() => navigate('/profile')}>
                Deposit Funds
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TableDetail;