// src/components/TableList.js
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { tableService, gameService } from "../services/apiService";

const TableList = () => {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeGames, setActiveGames] = useState([]);

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

  return (
    <div className="table-list">
      <h2>Available Poker Tables</h2>

      {tables.length === 0 ? (
        <p>No tables available</p>
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
                    <Link
                      to={`/games/${activeGame.id}`}
                      className="btn btn-primary"
                    >
                      {activeGame.status === "WAITING"
                        ? "Join Game"
                        : "Return to Game"}
                    </Link>
                  ) : (
                    <Link
                      to={`/tables/${table.id}`}
                      className="btn btn-primary"
                    >
                      View Table
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default TableList;
