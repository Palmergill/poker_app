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
  const [message, setMessage] = useState(null); // For temporary popup messages
  const [messageType, setMessageType] = useState("error"); // "error", "success", "info"
  const [handHistory, setHandHistory] = useState([]); // Store last 5 hand results
  const [actionType, setActionType] = useState("CHECK");
  const [betAmount, setBetAmount] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const messageTimeoutRef = useRef(null);

  useEffect(() => {
    const fetchGame = async () => {
      try {
        const response = await gameService.getGame(id);
        setGame(response.data);
        setLoading(false);

        // Connect to WebSocket after getting initial game state with small delay
        setTimeout(() => {
          connectWebSocket(response.data.id);
        }, 100); // Small delay to ensure state is set
      } catch (err) {
        console.error("Failed to load game:", err);
        showMessage("Failed to load game", "error");
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
      if (messageTimeoutRef.current) {
        clearTimeout(messageTimeoutRef.current);
      }
    };
  }, [id]);

  const showMessage = (text, type = "error", duration = 3000) => {
    // Clear any existing timeout
    if (messageTimeoutRef.current) {
      clearTimeout(messageTimeoutRef.current);
    }
    
    setMessage(text);
    setMessageType(type);
    
    // Auto-hide after duration
    messageTimeoutRef.current = setTimeout(() => {
      setMessage(null);
    }, duration);
  };

  const connectWebSocket = (gameId) => {
    // Check if WebSocket is supported
    if (!gameService.isWebSocketSupported()) {
      console.error("WebSocket is not supported in this browser");
      showMessage("Real-time updates not supported in this browser", "error");
      return;
    }

    setConnectionStatus("connecting");

    socketRef.current = gameService.connectToGameSocket(
      gameId,
      // onMessage
      (data) => {
        console.log("Game update received:", data);
        
        // Preserve any existing card data that might have been loaded from API
        setGame(currentGame => {
          if (!currentGame) {
            return data;
          }
          
          // Merge the update with existing game state, preserving player cards if they exist
          const updatedGame = { ...data };
          
          // If the incoming data has players with empty cards, but current game has cards, keep the existing cards
          if (updatedGame.players && currentGame.players) {
            updatedGame.players = updatedGame.players.map(newPlayer => {
              const existingPlayer = currentGame.players.find(p => p.id === newPlayer.id);
              
              // If existing player has cards but new player doesn't, keep existing cards
              if (existingPlayer && existingPlayer.cards && 
                  (!newPlayer.cards || 
                   (Array.isArray(newPlayer.cards) && newPlayer.cards.length === 0) ||
                   (newPlayer.cards.cards && newPlayer.cards.cards.length === 0))) {
                
                console.log(`Preserving cards for player ${newPlayer.player.user.username}`);
                return { ...newPlayer, cards: existingPlayer.cards };
              }
              
              return newPlayer;
            });
          }
          
          // Check for hand completion and update history
          if (updatedGame.winner_info && (!currentGame.winner_info || 
              JSON.stringify(updatedGame.winner_info) !== JSON.stringify(currentGame.winner_info))) {
            // New hand completed, add to history
            const winnerInfo = updatedGame.winner_info;
            const newHistoryEntry = {
              timestamp: Date.now(),
              winners: winnerInfo.winners,
              potAmount: winnerInfo.pot_amount,
              type: winnerInfo.type
            };
            
            setHandHistory(prevHistory => {
              const newHistory = [newHistoryEntry, ...prevHistory];
              return newHistory.slice(0, 5); // Keep only last 5 hands
            });
          }
          
          console.log("Updated game state:", updatedGame);
          return updatedGame;
        });
        
        setConnectionStatus("connected");
        setError(null); // Clear any previous errors
        setMessage(null); // Clear any popup messages
      },
      // onError
      (errorMessage) => {
        console.error("WebSocket error:", errorMessage);
        setConnectionStatus("error");
        showMessage(`Connection error: ${errorMessage}`, "error");

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
      showMessage("Failed to create WebSocket connection", "error");
    }
  };

  const handleStartGame = async () => {
    try {
      await gameService.startGame(id);
      // Game state will be updated via WebSocket
    } catch (err) {
      console.error("Failed to start game:", err);
      showMessage(err.response?.data?.error || "Failed to start game", "error");
    }
  };

  const handleLeaveGame = async () => {
    // Show confirmation dialog if game is in progress
    if (game.status === "PLAYING") {
      const confirmed = window.confirm(
        "Are you sure you want to leave? You are currently in an active game and may lose your seat and chips."
      );
      if (!confirmed) {
        return;
      }
    }

    try {
      await gameService.leaveGame(id);
      navigate("/tables");
    } catch (err) {
      console.error("Failed to leave game:", err);
      showMessage(err.response?.data?.error || "Failed to leave game", "error");
      
      // Even if the backend call fails, still navigate away after showing error
      // This ensures the player can always leave the UI even if there's a server issue
      setTimeout(() => {
        navigate("/tables");
      }, 2000);
    }
  };

  const handleRefreshGame = async () => {
    try {
      const response = await gameService.resetGameState(id);
      setGame(response.data.game);
      showMessage("✅ Game state refreshed successfully", "success");
    } catch (err) {
      console.error("Failed to refresh game:", err);
      showMessage(
        `Failed to refresh game: ${err.response?.data?.error || err.message}`,
        "error"
      );
    }
  };

  const handleAction = async (actionTypeParam = null, amountParam = null) => {
    try {
      const actionToUse = actionTypeParam || actionType;
      const amountToUse = amountParam !== null ? amountParam : betAmount;
      
      await gameService.takeAction(id, actionToUse, amountToUse);
      // Game state will be updated via WebSocket
      setError(null); // Clear any previous errors
      setMessage(null); // Clear any popup messages
    } catch (err) {
      console.error("Failed to take action:", err);
      showMessage(
        `${err.response?.data?.error || err.message}`,
        "error"
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
          top: "80px",
          right: "280px",
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

  if (!game && !loading) {
    return <div className="error">Game not found</div>;
  }

  const getCurrentUserInfo = () => {
    try {
      const userStr = localStorage.getItem("user");
      if (userStr) {
        const user = JSON.parse(userStr);
        console.log("Current user info:", user);
        return user;
      }

      console.warn("No user info found in localStorage");
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
            handleAction("FOLD");
          }}
        >
          Fold
        </button>

        {canCheck && (
          <button
            onClick={() => {
              handleAction("CHECK");
            }}
          >
            Check
          </button>
        )}

        {!canCheck && (
          <button
            onClick={() => {
              handleAction("CALL");
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
                  handleAction("BET", betAmount);
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
                  handleAction("RAISE", betAmount);
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
    const currentPlayer = findCurrentPlayer();

    return game.players.map((player) => {
      const isDealer = player.seat_position === game.dealer_position;
      const isTurn =
        game.current_player && game.current_player.id === player.player.id;

      let isCurrentUser = false;
      if (currentUser) {
        if (currentUser.id && player.player.user.id === currentUser.id) {
          isCurrentUser = true;
          console.log(`Player ${player.player.user.username} is current user (matched by ID)`);
        } else if (
          currentUser.username &&
          player.player.user.username === currentUser.username
        ) {
          isCurrentUser = true;
          console.log(`Player ${player.player.user.username} is current user (matched by username)`);
        }
      }
      
      // Handle new card data structure
      let playerCards = [];
      if (player.cards) {
        if (Array.isArray(player.cards)) {
          // Old format - array of card strings
          playerCards = player.cards;
        } else if (player.cards.cards) {
          // New format - object with cards array and owner info
          playerCards = player.cards.cards;
        }
      }
      
      console.log(`Player ${player.player.user.username}: isCurrentUser=${isCurrentUser}, hasCards=${playerCards && playerCards.length > 0}, cards:`, playerCards);

      let style = {};
      
      if (isCurrentUser) {
        // Current user always at bottom center
        style = {
          position: "absolute",
          left: "50%",
          bottom: "-140px",
          transform: "translateX(-50%)",
        };
      } else {
        // Other players positioned around the table (excluding current user's position)
        const otherPlayers = game.players.filter(p => {
          const isOtherCurrentUser = currentUser && (
            (currentUser.id && p.player.user.id === currentUser.id) ||
            (currentUser.username && p.player.user.username === currentUser.username)
          );
          return !isOtherCurrentUser;
        });
        
        const otherPlayerIndex = otherPlayers.findIndex(p => p.id === player.id);
        const totalOtherPlayers = otherPlayers.length;
        
        if (totalOtherPlayers === 1) {
          // Single opponent at top center
          style = {
            position: "absolute",
            left: "50%",
            top: "-120px",
            transform: "translateX(-50%)",
          };
        } else {
          // Multiple opponents distributed around the top arc
          const angle = (otherPlayerIndex / (totalOtherPlayers - 1)) * Math.PI - Math.PI/2;
          const radius = 350;
          
          style = {
            position: "absolute",
            left: `calc(50% + ${radius * Math.cos(angle)}px)`,
            top: `calc(50% + ${radius * Math.sin(angle) - 100}px)`,
            transform: "translate(-50%, -50%)",
          };
        }
      }

      return (
        <div
          key={player.id}
          className={`player-position ${isDealer ? "dealer" : ""} ${
            isTurn ? "active-turn" : ""
          } ${isCurrentUser ? "current-user" : "other-player"}`}
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

            {playerCards && playerCards.length > 0 && (
              <div className="player-cards">
                {playerCards.map((card, cardIndex) => {
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

  const renderPopupMessage = () => {
    if (!message) return null;

    const getMessageStyle = () => {
      const baseStyle = {
        position: "fixed",
        top: "120px",
        left: "50%",
        transform: "translateX(-50%)",
        padding: "20px 30px",
        borderRadius: "8px",
        fontSize: "16px",
        fontWeight: "bold",
        color: "white",
        zIndex: 2000,
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
        animation: "slideDown 0.3s ease-out",
        maxWidth: "400px",
        textAlign: "center",
      };

      switch (messageType) {
        case "success":
          return { ...baseStyle, backgroundColor: "#4caf50" };
        case "info":
          return { ...baseStyle, backgroundColor: "#2196f3" };
        case "error":
        default:
          return { ...baseStyle, backgroundColor: "#f44336" };
      }
    };

    return (
      <div style={getMessageStyle()}>
        {message}
      </div>
    );
  };

  const renderHandHistory = () => {
    if (handHistory.length === 0) {
      return (
        <div className="hand-history-card">
          <h3>Hand History</h3>
          <div className="history-empty">
            No hands completed yet
          </div>
        </div>
      );
    }

    return (
      <div className="hand-history-card">
        <h3>Recent Hands</h3>
        <div className="history-list">
          {handHistory.map((hand, index) => (
            <div key={hand.timestamp} className="history-entry">
              <div className="entry-number">#{handHistory.length - index}</div>
              <div className="entry-details">
                {hand.winners.length === 1 ? (
                  <div className="winner-info">
                    <div className="winner-name">{hand.winners[0].player_name}</div>
                    <div className="winner-amount">${hand.winners[0].winning_amount}</div>
                  </div>
                ) : (
                  <div className="winner-info">
                    <div className="winner-name">Split Pot</div>
                    <div className="winner-amount">${hand.potAmount}</div>
                  </div>
                )}
                {hand.winners[0].hand_name && (
                  <div className="hand-type">{hand.winners[0].hand_name}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderGameInfo = () => (
    <div className="game-info-card">
      <h3>{game.table.name}</h3>
      <div className="game-status-compact">
        <div><strong>Status:</strong> {game.status}</div>
        {game.phase && <div><strong>Phase:</strong> {game.phase}</div>}
        {game.current_bet > 0 && (
          <div><strong>Current Bet:</strong> ${game.current_bet}</div>
        )}
      </div>

      <div className="game-actions-compact">
        {game.status === "WAITING" && (
          <button onClick={handleStartGame} className="compact-btn">Start Game</button>
        )}
        {game.status === "PLAYING" && (
          <button onClick={handleRefreshGame} className="compact-btn refresh-button">
            Refresh
          </button>
        )}
        <button onClick={handleLeaveGame} className="compact-btn leave-btn" title="Leave table (always available)">
          Leave Table
        </button>
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
      {renderHandHistory()}
      {renderGameInfo()}
      <div className="poker-table">
        <div className="table-felt">
          {renderCommunityCards()}
          <div className="pot-display">Pot: ${game.pot}</div>
          {renderPlayers()}
        </div>
      </div>
      {renderActionButtons()}
      {renderGameLogs()}
      {renderPopupMessage()}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default PokerTable;
