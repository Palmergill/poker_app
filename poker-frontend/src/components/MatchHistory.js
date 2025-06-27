import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { playerService } from '../services/apiService';
import './MatchHistory.css';

const MatchHistory = () => {
  const navigate = useNavigate();
  const [matchHistory, setMatchHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    totalGames: 0,
    totalWinnings: 0,
    winRate: 0,
    avgWinLoss: 0
  });

  useEffect(() => {
    fetchMatchHistory();
  }, []);

  const fetchMatchHistory = async () => {
    try {
      setLoading(true);
      const response = await playerService.getMatchHistory();
      const history = response.data.match_history || [];
      setMatchHistory(history);
      
      // Calculate statistics (only for completed games)
      const completedGames = history.filter(game => game.status === 'COMPLETED');
      const totalCompletedGames = completedGames.length;
      const wins = completedGames.filter(game => game.user_result.win_loss > 0).length;
      const totalWinnings = completedGames.reduce((sum, game) => sum + game.user_result.win_loss, 0);
      const winRate = totalCompletedGames > 0 ? (wins / totalCompletedGames) * 100 : 0;
      const avgWinLoss = totalCompletedGames > 0 ? totalWinnings / totalCompletedGames : 0;
      
      setStats({
        totalGames: totalCompletedGames,
        totalWinnings,
        winRate,
        avgWinLoss
      });
    } catch (error) {
      console.error('Error fetching match history:', error);
      setError('Failed to load match history');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return `$${Math.abs(amount).toFixed(2)}`;
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const handleViewSummary = (gameId) => {
    navigate(`/games/${gameId}/summary`);
  };

  if (loading) {
    return (
      <div className="match-history-container">
        <div className="loading-spinner">Loading match history...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="match-history-container">
        <div className="error-message">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/tables')} className="btn-primary">
            Back to Tables
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="match-history-container">
      <div className="match-history-header">
        <h1>🏆 Match History</h1>
        <div className="stats-summary">
          <div className="stat-card">
            <h3>Total Games</h3>
            <p className="stat-value">{stats.totalGames}</p>
          </div>
          <div className="stat-card">
            <h3>Win Rate</h3>
            <p className="stat-value">{stats.winRate.toFixed(1)}%</p>
          </div>
          <div className="stat-card">
            <h3>Total P&L</h3>
            <p className={`stat-value ${stats.totalWinnings >= 0 ? 'positive' : 'negative'}`}>
              {stats.totalWinnings >= 0 ? '+' : ''}{formatCurrency(stats.totalWinnings)}
            </p>
          </div>
          <div className="stat-card">
            <h3>Avg Per Game</h3>
            <p className={`stat-value ${stats.avgWinLoss >= 0 ? 'positive' : 'negative'}`}>
              {stats.avgWinLoss >= 0 ? '+' : ''}{formatCurrency(stats.avgWinLoss)}
            </p>
          </div>
        </div>
      </div>

      <div className="match-history-content">
        {matchHistory.length === 0 ? (
          <div className="no-history">
            <h3>No Match History</h3>
            <p>You haven't completed any games yet. Join a table to start playing!</p>
            <button onClick={() => navigate('/tables')} className="btn-primary">
              Browse Tables
            </button>
          </div>
        ) : (
          <div className="history-table">
            <table>
              <thead>
                <tr>
                  <th>Table</th>
                  <th>Date</th>
                  <th>Hands</th>
                  <th>Players</th>
                  <th>Buy-in</th>
                  <th>Cash Out</th>
                  <th>P&L</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {matchHistory.map((game, index) => (
                  <tr key={index} className={
                    game.status === 'ONGOING' ? 'ongoing-game' : 
                    game.user_result.win_loss > 0 ? 'winning-game' : 
                    game.user_result.win_loss < 0 ? 'losing-game' : 'break-even-game'
                  }>
                    <td className="table-name">
                      {game.table_name}
                      {game.status === 'ONGOING' && <span className="ongoing-badge">ONGOING</span>}
                    </td>
                    <td>{game.completed_at ? formatDateTime(game.completed_at) : 'In Progress'}</td>
                    <td>{game.total_hands}</td>
                    <td>{game.total_players}</td>
                    <td>{formatCurrency(game.user_result.starting_stack)}</td>
                    <td>{formatCurrency(game.user_result.final_stack)}</td>
                    <td className={`win-loss ${game.user_result.win_loss > 0 ? 'positive' : game.user_result.win_loss < 0 ? 'negative' : 'neutral'}`}>
                      {game.user_result.win_loss > 0 ? '+' : ''}{formatCurrency(game.user_result.win_loss)}
                      {game.status === 'ONGOING' && <small> (current)</small>}
                    </td>
                    <td>
                      {game.status === 'ONGOING' ? (
                        <button 
                          onClick={() => navigate(`/games/${game.game_id}`)}
                          className="btn-primary btn-small"
                        >
                          Rejoin Game
                        </button>
                      ) : (
                        <button 
                          onClick={() => handleViewSummary(game.game_id)}
                          className="btn-secondary btn-small"
                        >
                          View Summary
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="match-history-actions">
        <button onClick={() => navigate('/tables')} className="btn-primary">
          Back to Tables
        </button>
      </div>
    </div>
  );
};

export default MatchHistory;