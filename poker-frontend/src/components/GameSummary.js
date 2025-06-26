import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { gameService } from '../services/apiService';
import './GameSummary.css';

const GameSummary = () => {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const [gameData, setGameData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchGameSummary();
  }, [gameId]);

  const fetchGameSummary = async () => {
    try {
      setLoading(true);
      const response = await gameService.getGameSummary(gameId);
      setGameData(response.data);
    } catch (error) {
      console.error('Error fetching game summary:', error);
      setError('Failed to load game summary');
    } finally {
      setLoading(false);
    }
  };

  const calculateSettlements = (players) => {
    if (!players || players.length === 0) return [];

    // Separate winners and losers
    const winners = players.filter(p => p.win_loss > 0).sort((a, b) => b.win_loss - a.win_loss);
    const losers = players.filter(p => p.win_loss < 0).sort((a, b) => a.win_loss - b.win_loss);
    
    const settlements = [];
    let winnerIndex = 0;
    let loserIndex = 0;

    while (winnerIndex < winners.length && loserIndex < losers.length) {
      const winner = winners[winnerIndex];
      const loser = losers[loserIndex];
      
      const winnerRemaining = winner.win_loss - (settlements
        .filter(s => s.from === winner.player_name)
        .reduce((sum, s) => sum + s.amount, 0) - settlements
        .filter(s => s.to === winner.player_name)
        .reduce((sum, s) => sum + s.amount, 0));
      
      const loserOwes = Math.abs(loser.win_loss) - settlements
        .filter(s => s.from === loser.player_name)
        .reduce((sum, s) => sum + s.amount, 0);

      const settlementAmount = Math.min(winnerRemaining, loserOwes);

      if (settlementAmount > 0.01) { // Avoid tiny amounts due to floating point
        settlements.push({
          from: loser.player_name,
          to: winner.player_name,
          amount: settlementAmount
        });
      }

      // Move to next winner or loser based on who is "satisfied"
      if (winnerRemaining <= settlementAmount + 0.01) {
        winnerIndex++;
      }
      if (loserOwes <= settlementAmount + 0.01) {
        loserIndex++;
      }
    }

    return settlements;
  };

  const formatCurrency = (amount) => {
    return `$${Math.abs(amount).toFixed(2)}`;
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="game-summary-container">
        <div className="loading-spinner">Loading game summary...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="game-summary-container">
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

  if (!gameData || !gameData.game_summary) {
    return (
      <div className="game-summary-container">
        <div className="error-message">
          <h2>No Summary Available</h2>
          <p>This game does not have a summary available yet.</p>
          <button onClick={() => navigate('/tables')} className="btn-primary">
            Back to Tables
          </button>
        </div>
      </div>
    );
  }

  const { game_summary } = gameData;
  const settlements = calculateSettlements(game_summary.players);
  const totalPot = game_summary.players.reduce((sum, p) => sum + p.starting_stack, 0);

  return (
    <div className="game-summary-container">
      <div className="game-summary-header">
        <h1>🎮 Game Summary</h1>
        <div className="game-info">
          <h2>{game_summary.table_name}</h2>
          <p><strong>Game ID:</strong> {game_summary.game_id}</p>
          <p><strong>Completed:</strong> {formatDateTime(game_summary.completed_at)}</p>
          <p><strong>Total Hands:</strong> {game_summary.total_hands}</p>
          <p><strong>Total Buy-ins:</strong> {formatCurrency(totalPot)}</p>
        </div>
      </div>

      <div className="summary-content">
        {/* Player Results Table */}
        <div className="results-section">
          <h3>📊 Player Results</h3>
          <div className="results-table">
            <table>
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Buy-in</th>
                  <th>Cash Out</th>
                  <th>Win/Loss</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {game_summary.players.map((player, index) => (
                  <tr key={index} className={player.win_loss > 0 ? 'winner' : player.win_loss < 0 ? 'loser' : 'break-even'}>
                    <td className="player-name">{player.player_name}</td>
                    <td>{formatCurrency(player.starting_stack)}</td>
                    <td>{formatCurrency(player.final_stack)}</td>
                    <td className={`win-loss ${player.win_loss > 0 ? 'positive' : player.win_loss < 0 ? 'negative' : 'neutral'}`}>
                      {player.win_loss > 0 ? '+' : ''}{formatCurrency(player.win_loss)}
                    </td>
                    <td className="status">{player.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Settlement Instructions */}
        {settlements.length > 0 && (
          <div className="settlement-section">
            <h3>💰 Settlement Instructions</h3>
            <p className="settlement-description">
              To settle up, the following payments should be made:
            </p>
            <div className="settlement-table">
              <table>
                <thead>
                  <tr>
                    <th>From</th>
                    <th>To</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {settlements.map((settlement, index) => (
                    <tr key={index}>
                      <td className="from-player">{settlement.from}</td>
                      <td className="to-player">{settlement.to}</td>
                      <td className="settlement-amount">{formatCurrency(settlement.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="settlement-note">
              <p><strong>Note:</strong> These settlements ensure everyone gets their correct winnings/losses.</p>
            </div>
          </div>
        )}

        {settlements.length === 0 && (
          <div className="no-settlement-section">
            <h3>✅ No Settlements Needed</h3>
            <p>All players broke even or no money changed hands.</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="summary-actions">
          <button 
            onClick={() => navigate('/tables')} 
            className="btn-primary"
          >
            Back to Tables
          </button>
          <button 
            onClick={() => window.print()} 
            className="btn-secondary"
          >
            Print Summary
          </button>
          <button 
            onClick={() => {
              const summaryText = `Game Summary - ${game_summary.table_name}\n` +
                `Game ID: ${game_summary.game_id}\n` +
                `Completed: ${formatDateTime(game_summary.completed_at)}\n\n` +
                `Player Results:\n` +
                game_summary.players.map(p => 
                  `${p.player_name}: ${formatCurrency(p.starting_stack)} → ${formatCurrency(p.final_stack)} (${p.win_loss > 0 ? '+' : ''}${formatCurrency(p.win_loss)})`
                ).join('\n') +
                (settlements.length > 0 ? '\n\nSettlements:\n' + 
                  settlements.map(s => `${s.from} pays ${s.to}: ${formatCurrency(s.amount)}`).join('\n') : 
                  '\n\nNo settlements needed.');
              
              navigator.clipboard.writeText(summaryText);
              alert('Summary copied to clipboard!');
            }}
            className="btn-secondary"
          >
            Copy to Clipboard
          </button>
        </div>
      </div>
    </div>
  );
};

export default GameSummary;