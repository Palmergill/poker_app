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

  return (
    <div className="table-list">
      <div className="table-list-header">
        <h2>Available Poker Tables</h2>
        <Link to="/tables/create" className="btn btn-success create-table-btn">
          Create New Table
        </Link>
      </div>

      {tables.length === 0 ? (
        <div className="no-tables">
          <p>No tables available yet</p>
          <Link to="/tables/create" className="btn btn-primary">
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
                        className="btn btn-primary"
                      >
                        {activeGame.status === "WAITING"
                          ? "Join Game"
                          : "Return to Game"}
                      </Link>
                      <button
                        onClick={() => handleDeleteClick(table)}
                        className="btn btn-danger delete-table-btn"
                      >
                        Delete Table
                      </button>
                      {activeGame.status === "PLAYING" && (
                        <button
                          onClick={() => handleDeleteGameClick(activeGame, table)}
                          className="btn btn-danger delete-game-btn"
                        >
                          Delete Game
                        </button>
                      )}
                    </>
                  ) : (
                    <>
                      <Link
                        to={`/tables/${table.id}`}
                        className="btn btn-primary"
                      >
                        View Table
                      </Link>
                      <button
                        onClick={() => handleDeleteClick(table)}
                        className="btn btn-danger delete-table-btn"
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
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="btn btn-danger"
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
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteGameConfirm}
                className="btn btn-danger"
              >
                Delete Game
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TableList;
