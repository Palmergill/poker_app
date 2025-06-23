// src/components/TableList.js
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { tableService, gameService, authService } from "../services/apiService";

const TableList = () => {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeGames, setActiveGames] = useState([]);
  const [deleteConfirm, setDeleteConfirm] = useState(null); // {tableId, tableName}
  const [deleteGameConfirm, setDeleteGameConfirm] = useState(null); // {gameId, tableName}
  const [deleteAllConfirm, setDeleteAllConfirm] = useState(false);
  const [joinTableId, setJoinTableId] = useState(null);
  const [buyInAmount, setBuyInAmount] = useState('');
  const isAdmin = authService.isAdmin();

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const response = await tableService.getTables();
        setTables(response.data);
        setLoading(false);
      } catch (err) {
        setError("Failed to load tables");
        setLoading(false);
      }
    };

    const fetchActiveGames = async () => {
      try {
        const response = await gameService.getGames();
        setActiveGames(response.data);
      } catch (err) {
        console.error("Failed to load active games");
      }
    };

    fetchTables();
    fetchActiveGames();
  }, []);

  if (loading) {
    return <div className="loading">Loading tables...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  const getActiveGameForTable = (tableId) => {
    return activeGames.find((game) => game.table.id === tableId);
  };

  const handleDeleteClick = (table) => {
    setDeleteConfirm({ tableId: table.id, tableName: table.name });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm) return;

    try {
      setError(null);
      await tableService.deleteTable(deleteConfirm.tableId);
      
      // Remove the table from the local state
      setTables(tables.filter(table => table.id !== deleteConfirm.tableId));
      setDeleteConfirm(null);
      
      // Show success message briefly
      setError("✅ Table deleted successfully");
      setTimeout(() => setError(null), 3000);
    } catch (err) {
      console.error("Failed to delete table:", err);
      setError(
        `Failed to delete table: ${err.response?.data?.error || err.message}`
      );
      setDeleteConfirm(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirm(null);
  };

  const handleDeleteGameClick = (game, table) => {
    setDeleteGameConfirm({ gameId: game.id, tableName: table.name });
  };

  const handleDeleteGameConfirm = async () => {
    if (!deleteGameConfirm) return;

    try {
      setError(null);
      await gameService.deleteGame(deleteGameConfirm.gameId);
      
      // Remove the game from activeGames state
      setActiveGames(activeGames.filter(game => game.id !== deleteGameConfirm.gameId));
      setDeleteGameConfirm(null);
      
      // Show success message briefly
      setError("✅ Game deleted successfully");
      setTimeout(() => setError(null), 3000);
    } catch (err) {
      console.error("Failed to delete game:", err);
      setError(
        `Failed to delete game: ${err.response?.data?.error || err.message}`
      );
      setDeleteGameConfirm(null);
    }
  };

  const handleDeleteGameCancel = () => {
    setDeleteGameConfirm(null);
  };

  const handleDeleteAllClick = () => {
    setDeleteAllConfirm(true);
  };

  const handleDeleteAllConfirm = async () => {
    try {
      setError(null);
      const response = await tableService.deleteAllTables();
      
      // Clear all tables and games from state
      setTables([]);
      setActiveGames([]);
      setDeleteAllConfirm(false);
      
      // Show success message
      setError(`✅ ${response.data.message}`);
      setTimeout(() => setError(null), 3000);
    } catch (err) {
      console.error("Failed to delete all tables:", err);
      setError(
        `Failed to delete all tables: ${err.response?.data?.error || err.message}`
      );
      setDeleteAllConfirm(false);
    }
  };

  const handleDeleteAllCancel = () => {
    setDeleteAllConfirm(false);
  };

  const handleJoinTableClick = (table) => {
    setJoinTableId(table.id);
    setBuyInAmount(table.min_buy_in.toString());
  };

  const handleJoinTableConfirm = async () => {
    if (!joinTableId || !buyInAmount) return;

    try {
      setError(null);
      const response = await tableService.joinTable(joinTableId, parseFloat(buyInAmount));
      
      // Redirect to the game
      window.location.href = `/games/${response.data.id}`;
    } catch (err) {
      console.error("Failed to join table:", err);
      setError(
        `Failed to join table: ${err.response?.data?.error || err.message}`
      );
      setJoinTableId(null);
    }
  };

  const handleJoinTableCancel = () => {
    setJoinTableId(null);
    setBuyInAmount('');
  };

  return (
    <div className="table-list">
      <div className="table-list-header">
        <h2>Available Poker Tables</h2>
        <div className="header-buttons">
          <Link to="/tables/create" className="btn btn-success btn-sm create-table-btn">
            Create New Table
          </Link>
          {isAdmin && tables.length > 0 && (
            <button
              onClick={handleDeleteAllClick}
              className="btn btn-danger btn-sm delete-all-btn"
            >
              Delete All Tables
            </button>
          )}
        </div>
      </div>

      {tables.length === 0 ? (
        <div className="no-tables">
          <p>No tables available yet</p>
          <Link to="/tables/create" className="btn btn-primary btn-sm">
            Create the First Table
          </Link>
        </div>
      ) : (
        <div className="table-grid">
          {tables.map((table) => {
            const activeGame = getActiveGameForTable(table.id);

            return (
              <div key={table.id} className="table-card">
                <h3>{table.name}</h3>
                <div className="table-info">
                  <p>
                    <strong>Blinds:</strong> ${table.small_blind}/$
                    {table.big_blind}
                  </p>
                  <p>
                    <strong>Buy-in:</strong> ${table.min_buy_in} - $
                    {table.max_buy_in}
                  </p>
                  <p>
                    <strong>Max Players:</strong> {table.max_players}
                  </p>

                  {activeGame && (
                    <p>
                      <strong>Status:</strong> {activeGame.status}
                      {activeGame.status === "PLAYING" &&
                        ` (${
                          activeGame.players.filter((p) => p.is_active).length
                        } active)`}
                    </p>
                  )}
                </div>

                <div className="table-actions">
                  {activeGame ? (
                    <>
                      <Link
                        to={`/games/${activeGame.id}`}
                        className="btn btn-primary btn-sm"
                      >
                        {activeGame.status === "WAITING"
                          ? "Join Game"
                          : "Return to Game"}
                      </Link>
                      <button
                        onClick={() => handleJoinTableClick(table)}
                        className="btn btn-success btn-sm join-table-btn"
                      >
                        Join Table
                      </button>
                      <button
                        onClick={() => handleDeleteClick(table)}
                        className="btn btn-danger btn-sm delete-table-btn"
                      >
                        Delete Table
                      </button>
                      {activeGame.status === "PLAYING" && (
                        <button
                          onClick={() => handleDeleteGameClick(activeGame, table)}
                          className="btn btn-danger btn-sm delete-game-btn"
                        >
                          Delete Game
                        </button>
                      )}
                    </>
                  ) : (
                    <>
                      <Link
                        to={`/tables/${table.id}`}
                        className="btn btn-primary btn-sm"
                      >
                        View Table
                      </Link>
                      <button
                        onClick={() => handleJoinTableClick(table)}
                        className="btn btn-success btn-sm join-table-btn"
                      >
                        Join Table
                      </button>
                      <button
                        onClick={() => handleDeleteClick(table)}
                        className="btn btn-danger btn-sm delete-table-btn"
                      >
                        Delete Table
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="delete-modal-overlay">
          <div className="delete-modal">
            <h3>Delete Table</h3>
            <p>
              Are you sure you want to delete the table "{deleteConfirm.tableName}"?
            </p>
            <p className="delete-warning">
              This action cannot be undone.
            </p>
            <div className="delete-modal-actions">
              <button
                onClick={handleDeleteCancel}
                className="btn btn-secondary btn-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="btn btn-danger btn-sm"
              >
                Delete Table
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Game Confirmation Modal */}
      {deleteGameConfirm && (
        <div className="delete-modal-overlay">
          <div className="delete-modal">
            <h3>Delete Active Game</h3>
            <p>
              Are you sure you want to delete the active game at table "{deleteGameConfirm.tableName}"?
            </p>
            <p className="delete-warning">
              This will forcibly end the game in progress and kick out all players. This action cannot be undone.
            </p>
            <div className="delete-modal-actions">
              <button
                onClick={handleDeleteGameCancel}
                className="btn btn-secondary btn-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteGameConfirm}
                className="btn btn-danger btn-sm"
              >
                Delete Game
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete All Tables Confirmation Modal */}
      {deleteAllConfirm && (
        <div className="delete-modal-overlay">
          <div className="delete-modal">
            <h3>Delete All Tables</h3>
            <p>
              Are you sure you want to delete ALL {tables.length} tables?
            </p>
            <p className="delete-warning">
              This will delete all tables, games, and kick out all players. This action cannot be undone.
            </p>
            <div className="delete-modal-actions">
              <button
                onClick={handleDeleteAllCancel}
                className="btn btn-secondary btn-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAllConfirm}
                className="btn btn-danger btn-sm"
              >
                Delete All Tables
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Join Table Modal */}
      {joinTableId && (
        <div className="delete-modal-overlay">
          <div className="delete-modal">
            <h3>Join Table</h3>
            <p>Enter your buy-in amount:</p>
            <div className="join-table-form">
              <label htmlFor="buyInAmount">Buy-in Amount ($):</label>
              <input
                type="number"
                id="buyInAmount"
                value={buyInAmount}
                onChange={(e) => setBuyInAmount(e.target.value)}
                min={tables.find(t => t.id === joinTableId)?.min_buy_in || 0}
                max={tables.find(t => t.id === joinTableId)?.max_buy_in || 1000}
                step="0.01"
                className="form-input"
              />
              <p className="buy-in-range">
                Range: ${tables.find(t => t.id === joinTableId)?.min_buy_in} - $
                {tables.find(t => t.id === joinTableId)?.max_buy_in}
              </p>
            </div>
            <div className="delete-modal-actions">
              <button
                onClick={handleJoinTableCancel}
                className="btn btn-secondary btn-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleJoinTableConfirm}
                className="btn btn-success btn-sm"
                disabled={!buyInAmount || parseFloat(buyInAmount) < (tables.find(t => t.id === joinTableId)?.min_buy_in || 0)}
              >
                Join Table
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TableList;
