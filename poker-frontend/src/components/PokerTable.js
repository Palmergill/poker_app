// src/components/PokerTable.js
import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { gameService } from "../services/apiService";
import "./PokerTable.css";

const PokerTable = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [game, setGame] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionType, setActionType] = useState("CHECK");
  const [betAmount, setBetAmount] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    const fetchGame = async () => {
      try {
        const response = await gameService.getGame(id);
        setGame(response.data);
        setLoading(false);

        // Connect to WebSocket after getting initial game state
        connectWebSocket(response.data.id);
      } catch (err) {
        console.error("Failed to load game:", err);
        setError("Failed to load game");
        setLoading(false);
      }
    };

    fetchGame();

    // Cleanup function
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [id]);

  const connectWebSocket = (gameId) => {
    // Check if WebSocket is supported
    if (!gameService.isWebSocketSupported()) {
      console.error("WebSocket is not supported in this browser");
      setError("Real-time updates not supported in this browser");
      return;
    }

    setConnectionStatus("connecting");

    socketRef.current = gameService.connectToGameSocket(
      gameId,
      // onMessage
      (data) => {
        console.log("Game update received:", data);
        setGame(data);
        setConnectionStatus("connected");
        setError(null); // Clear any previous errors
      },
      // onError
      (errorMessage) => {
        console.error("WebSocket error:", errorMessage);
        setConnectionStatus("error");
        setError(`Connection error: ${errorMessage}`);

        // Try to reconnect after 3 seconds
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("Attempting to reconnect WebSocket...");
          connectWebSocket(gameId);
        }, 3000);
      },
      // onClose
      (event) => {
        setConnectionStatus("disconnected");

        // Only try to reconnect if it wasn't a normal closure or authentication issue
        if (event.code !== 1000 && event.code !== 4001 && event.code !== 4003) {
          console.log(
            "WebSocket closed unexpectedly, attempting to reconnect..."
          );

          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }

          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket(gameId);
          }, 3000);
        }
      }
    );

    if (!socketRef.current) {
      setConnectionStatus("error");
      setError("Failed to create WebSocket connection");
    }
  };

  const handleStartGame = async () => {
    try {
      await gameService.startGame(id);
      // Game state will be updated via WebSocket
    } catch (err) {
      console.error("Failed to start game:", err);
      setError(err.response?.data?.error || "Failed to start game");
    }
  };

  const handleLeaveGame = async () => {
    try {
      await gameService.leaveGame(id);
      navigate("/tables");
    } catch (err) {
      console.error("Failed to leave game:", err);
      setError(err.response?.data?.error || "Failed to leave game");
    }
  };

  const handleAction = async () => {
    try {
      await gameService.takeAction(id, actionType, betAmount);
      // Game state will be updated via WebSocket
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error("Failed to take action:", err);
      setError(
        `Failed to take action: ${err.response?.data?.error || err.message}`
      );
    }
  };

  const renderConnectionStatus = () => {
    const statusColors = {
      connected: "#4caf50",
      connecting: "#ff9800",
      disconnected: "#f44336",
      error: "#f44336",
    };

    return (
      <div
        style={{
          position: "fixed",
          top: "10px",
          right: "10px",
          padding: "5px 10px",
          borderRadius: "15px",
          backgroundColor: statusColors[connectionStatus] || "#ccc",
          color: "white",
          fontSize: "12px",
          zIndex: 1000,
        }}
      >
        {connectionStatus === "connected" && "🟢 Connected"}
        {connectionStatus === "connecting" && "🟡 Connecting..."}
        {connectionStatus === "disconnected" && "🔴 Disconnected"}
        {connectionStatus === "error" && "❌ Error"}
      </div>
    );
  };

  if (loading) {
    return <div className="loading">Loading game...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!game) {
    return <div className="error">Game not found</div>;
  }

  const getCurrentUserInfo = () => {
    try {
      const userStr = localStorage.getItem("user");
      if (userStr) {
        const user = JSON.parse(userStr);
        return user;
      }

      const token = localStorage.getItem("accessToken");
      if (token && game.players) {
        return null;
      }

      return null;
    } catch (e) {
      console.error("Error getting user info:", e);
      return null;
    }
  };

  const findCurrentPlayer = () => {
    if (!game.players) return null;

    const currentUser = getCurrentUserInfo();
    if (!currentUser) return null;

    if (currentUser.id) {
      const playerById = game.players.find(
        (p) => p.player.user.id === currentUser.id
      );
      if (playerById) return playerById;
    }

    if (currentUser.username) {
      const playerByUsername = game.players.find(
        (p) => p.player.user.username === currentUser.username
      );
      if (playerByUsername) return playerByUsername;
    }

    return null;
  };

  const isPlayerTurn = () => {
    const currentPlayer = findCurrentPlayer();
    return (
      currentPlayer &&
      game.current_player &&
      game.current_player.id === currentPlayer.player.id
    );
  };

  const renderActionButtons = () => {
    if (game.status !== "PLAYING" || !isPlayerTurn()) {
      return null;
    }

    const currentPlayer = findCurrentPlayer();
    if (!currentPlayer) return null;

    const currentBet = parseFloat(game.current_bet || 0);
    const playerBet = parseFloat(currentPlayer.current_bet || 0);
    const playerStack = parseFloat(currentPlayer.stack || 0);

    const canCheck = currentBet === playerBet;
    const minBet = parseFloat(game.table.big_blind);
    const minRaise = currentBet * 2;

    return (
      <div className="action-controls">
        <button
          onClick={() => {
            setActionType("FOLD");
            handleAction();
          }}
        >
          Fold
        </button>

        {canCheck && (
          <button
            onClick={() => {
              setActionType("CHECK");
              handleAction();
            }}
          >
            Check
          </button>
        )}

        {!canCheck && (
          <button
            onClick={() => {
              setActionType("CALL");
              handleAction();
            }}
          >
            Call ${(currentBet - playerBet).toFixed(2)}
          </button>
        )}

        {currentBet === 0 && (
          <>
            <div className="bet-controls">
              <input
                type="number"
                min={minBet}
                max={playerStack}
                step="0.01"
                value={betAmount}
                onChange={(e) => setBetAmount(parseFloat(e.target.value) || 0)}
                placeholder={`Min: $${minBet}`}
              />
              <button
                disabled={betAmount < minBet || betAmount > playerStack}
                onClick={() => {
                  setActionType("BET");
                  handleAction();
                }}
              >
                Bet ${betAmount || 0}
              </button>
            </div>
          </>
        )}

        {currentBet > 0 && (
          <>
            <div className="bet-controls">
              <input
                type="number"
                min={minRaise}
                max={playerStack + playerBet}
                step="0.01"
                value={betAmount}
                onChange={(e) => setBetAmount(parseFloat(e.target.value) || 0)}
                placeholder={`Min: $${minRaise}`}
              />
              <button
                disabled={
                  betAmount < minRaise || betAmount > playerStack + playerBet
                }
                onClick={() => {
                  setActionType("RAISE");
                  handleAction();
                }}
              >
                Raise to ${betAmount || 0}
              </button>
            </div>
          </>
        )}
      </div>
    );
  };

  const renderPlayers = () => {
    if (!game.players || game.players.length === 0) {
      return <div className="no-players">No players at the table</div>;
    }

    const currentUser = getCurrentUserInfo();

    return game.players.map((player) => {
      const isDealer = player.seat_position === game.dealer_position;
      const isTurn =
        game.current_player && game.current_player.id === player.player.id;

      let isCurrentUser = false;
      if (currentUser) {
        if (currentUser.id && player.player.user.id === currentUser.id) {
          isCurrentUser = true;
        } else if (
          currentUser.username &&
          player.player.user.username === currentUser.username
        ) {
          isCurrentUser = true;
        }
      }

      const totalSeats = game.table.max_players;
      const angle =
        (player.seat_position / totalSeats) * 2 * Math.PI - Math.PI / 2;
      const radius = 280;

      const style = {
        position: "absolute",
        left: `calc(50% + ${radius * Math.cos(angle)}px)`,
        top: `calc(50% + ${radius * Math.sin(angle)}px)`,
        transform: "translate(-50%, -50%)",
      };

      return (
        <div
          key={player.id}
          className={`player-position ${isDealer ? "dealer" : ""} ${
            isTurn ? "active-turn" : ""
          } ${isCurrentUser ? "current-user" : ""}`}
          style={style}
        >
          <div className="player-info">
            <div className="player-name">
              {player.player.user.username}
              {isCurrentUser && <span className="you-indicator"> (You)</span>}
            </div>
            <div className="player-stack">${player.stack}</div>

            {player.current_bet > 0 && (
              <div className="player-bet">${player.current_bet}</div>
            )}

            {player.cards && player.cards.length > 0 && (
              <div className="player-cards">
                {player.cards.map((card, cardIndex) => {
                  const showCard = isCurrentUser || game.phase === "SHOWDOWN";

                  if (!showCard) {
                    return (
                      <div key={cardIndex} className="card hidden">
                        <div className="card-back"></div>
                      </div>
                    );
                  }

                  const rank = card.slice(0, -1);
                  const suit = card.slice(-1);

                  const suitSymbols = {
                    S: "♠",
                    H: "♥",
                    D: "♦",
                    C: "♣",
                  };

                  return (
                    <div
                      key={cardIndex}
                      className="card visible"
                      data-suit={suit}
                    >
                      <div className="card-rank">{rank}</div>
                      <div className="card-suit">{suitSymbols[suit]}</div>
                    </div>
                  );
                })}
              </div>
            )}

            {!player.is_active && <div className="player-status">Folded</div>}
          </div>
        </div>
      );
    });
  };

  const renderGameInfo = () => (
    <div className="game-info">
      <h2>{game.table.name}</h2>
      <div className="game-status">
        <div>
          <strong>Status:</strong> {game.status}
        </div>
        {game.phase && (
          <div>
            <strong>Phase:</strong> {game.phase}
          </div>
        )}
        <div>
          <strong>Pot:</strong> ${game.pot}
        </div>
        {game.current_bet > 0 && (
          <div>
            <strong>Current Bet:</strong> ${game.current_bet}
          </div>
        )}
      </div>

      <div className="game-actions">
        {game.status === "WAITING" && (
          <button onClick={handleStartGame}>Start Game</button>
        )}
        <button onClick={handleLeaveGame}>Leave Table</button>
      </div>
    </div>
  );

  const renderCommunityCards = () => {
    if (!game.community_cards || game.community_cards.length === 0) {
      return null;
    }

    return (
      <div className="community-cards">
        {game.community_cards.map((card, index) => {
          const rank = card.slice(0, -1);
          const suit = card.slice(-1);

          const suitSymbols = {
            S: "♠",
            H: "♥",
            D: "♦",
            C: "♣",
          };

          return (
            <div
              key={index}
              className="card community-card visible"
              data-suit={suit}
            >
              <div className="card-rank">{rank}</div>
              <div className="card-suit">{suitSymbols[suit]}</div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderGameLogs = () => {
    if (!game.actions || game.actions.length === 0) {
      return null;
    }

    return (
      <div className="game-logs">
        <h3>Recent Actions</h3>
        <ul>
          {game.actions.map((action, index) => (
            <li key={index}>
              <strong>{action.player}:</strong> {action.action_type}
              {(action.action_type === "BET" ||
                action.action_type === "RAISE") &&
                ` $${action.amount}`}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="poker-game-container">
      {renderConnectionStatus()}
      {renderGameInfo()}
      <div className="poker-table">
        <div className="table-felt">
          {renderCommunityCards()}
          {game.pot > 0 && <div className="pot-display">Pot: ${game.pot}</div>}
          {renderPlayers()}
        </div>
      </div>
      {renderActionButtons()}
      {renderGameLogs()}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default PokerTable;
