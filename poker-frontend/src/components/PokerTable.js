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
  const socketRef = useRef(null);

  useEffect(() => {
    const fetchGame = async () => {
      try {
        const response = await gameService.getGame(id);
        setGame(response.data);
        setLoading(false);

        // Connect to WebSocket after getting initial game state
        connectWebSocket(response.data.id);
      } catch (err) {
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
    };
  }, [id]);

  const connectWebSocket = (gameId) => {
    socketRef.current = gameService.connectToGameSocket(gameId, (data) => {
      // Update game state when we receive WebSocket message
      setGame(data);
    });

    socketRef.current.onopen = () => {
      console.log("WebSocket connected");
    };

    socketRef.current.onclose = () => {
      console.log("WebSocket disconnected");
    };

    socketRef.current.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  };

  const handleStartGame = async () => {
    try {
      await gameService.startGame(id);
    } catch (err) {
      setError("Failed to start game");
    }
  };

  const handleLeaveGame = async () => {
    try {
      await gameService.leaveGame(id);
      navigate("/tables");
    } catch (err) {
      setError("Failed to leave game");
    }
  };

  const handleAction = async () => {
    try {
      await gameService.takeAction(id, actionType, betAmount);
      setError(null); // Clear any previous errors
    } catch (err) {
      setError(
        `Failed to take action: ${err.response?.data?.error || err.message}`
      );
    }
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

  // Get current user info - try multiple ways
  const getCurrentUserInfo = () => {
    try {
      // First try to get from localStorage
      const userStr = localStorage.getItem("user");
      if (userStr) {
        const user = JSON.parse(userStr);
        return user;
      }

      // If not in localStorage, try to get from the access token
      // The backend might be sending user info in the game data
      const token = localStorage.getItem("accessToken");
      if (token && game.players) {
        // Look for the player that matches the current session
        // This is a fallback - ideally the user info should be in localStorage
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

    // Try to match by user ID first
    if (currentUser.id) {
      const playerById = game.players.find(
        (p) => p.player.user.id === currentUser.id
      );
      if (playerById) return playerById;
    }

    // Try to match by username as fallback
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

      // Check if this is the current user by multiple methods
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

      // Calculate position based on seat number and total seats
      const totalSeats = game.table.max_players;
      const angle =
        (player.seat_position / totalSeats) * 2 * Math.PI - Math.PI / 2;
      const radius = 280; // Distance from center

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
                  // Show cards for current user or during showdown
                  const showCard = isCurrentUser || game.phase === "SHOWDOWN";

                  if (!showCard) {
                    // Hidden card
                    return (
                      <div key={cardIndex} className="card hidden">
                        <div className="card-back"></div>
                      </div>
                    );
                  }

                  // Parse card string (e.g., "AS" -> rank: "A", suit: "S")
                  const rank = card.slice(0, -1);
                  const suit = card.slice(-1);

                  // Unicode suit symbols
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
          // Parse card string (e.g., "AS" -> rank: "A", suit: "S")
          const rank = card.slice(0, -1);
          const suit = card.slice(-1);

          // Unicode suit symbols
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
