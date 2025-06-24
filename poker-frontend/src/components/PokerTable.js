// src/components/PokerTable.js
import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { gameService } from "../services/apiService";
import "./PokerTable.css";

// Main poker table component for displaying and interacting with poker games
const PokerTable = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [game, setGame] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null); // For temporary popup messages
  const [messageType, setMessageType] = useState("error"); // "error", "success", "info"
  const [handHistory, setHandHistory] = useState([]); // Store last 5 hand results
  const [showHandResults, setShowHandResults] = useState(false); // Show hand results popup
  const [currentHandResult, setCurrentHandResult] = useState(null); // Current hand result data
  const [actionType, setActionType] = useState("CHECK");
  const [betAmount, setBetAmount] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const messageTimeoutRef = useRef(null);

  useEffect(() => {
    // Fetch initial game data and hand history
    const fetchGame = async () => {
      try {
        const response = await gameService.getGame(id);
        setGame(response.data);
        
        // Fetch hand history for this game
        try {
          const historyResponse = await gameService.getHandHistory(id);
          
          if (historyResponse.data && historyResponse.data.hand_history) {
            // Transform backend format to frontend format
            const formattedHistory = historyResponse.data.hand_history.map(hand => {
              const winnerInfo = hand.winner_info;
              const potAmount = winnerInfo?.pot_amount || parseFloat(hand.pot_amount) || 0;
              
              return {
                timestamp: new Date(hand.completed_at).getTime(),
                winners: winnerInfo?.winners || [],
                potAmount: potAmount,
                type: winnerInfo?.type || 'Unknown',
                handNumber: hand.hand_number
              };
            });
            setHandHistory(formattedHistory.slice(0, 5)); // Keep only last 5 hands
          }
        } catch (historyErr) {
          // Don't show error to user, hand history is not critical
        }
        
        setLoading(false);

        // Connect to WebSocket after getting initial game state with small delay
        setTimeout(() => {
          connectWebSocket(response.data.id);
        }, 100); // Small delay to ensure state is set
      } catch (err) {
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

  // Poll for game updates every 3 seconds as backup to WebSocket
  useEffect(() => {
    if (!game) return; // Don't poll until we have initial game data
    
    const pollInterval = setInterval(async () => {
      try {
        // Fetch updated game data
        const response = await gameService.getGame(id);
        const updatedGame = response.data;
        setGame(updatedGame);
        
        // Check if we need to restore hand results popup after browser refresh
        // This happens when game phase is WAITING_FOR_PLAYERS but we don't have a popup showing
        if (updatedGame.phase === 'WAITING_FOR_PLAYERS' && 
            updatedGame.winner_info && 
            !showHandResults) {
          
          console.log('🔄 Restoring hand results popup after browser refresh');
          
          // Handle winner_info which comes from API as already parsed object
          let winnerInfo;
          if (typeof updatedGame.winner_info === 'string') {
            try {
              winnerInfo = JSON.parse(updatedGame.winner_info);
            } catch (e) {
              console.warn('Failed to parse winner_info as JSON:', e);
              winnerInfo = {};
            }
          } else {
            // Already an object
            winnerInfo = updatedGame.winner_info || {};
          }
          
          const restoredHandResult = {
            timestamp: Date.now(),
            winners: winnerInfo.winners || [],
            potAmount: winnerInfo.pot_amount || 0,
            type: winnerInfo.type || 'Unknown',
            handNumber: updatedGame.hand_count || 1,
            allPlayers: updatedGame.players || []
          };
          
          setCurrentHandResult(restoredHandResult);
          setShowHandResults(true);
          console.log('✅ Hand results popup restored');
        }
        
        // Fetch updated hand history
        const historyResponse = await gameService.getHandHistory(id);
        if (historyResponse.data && historyResponse.data.hand_history) {
          const formattedHistory = historyResponse.data.hand_history.map(hand => {
            const winnerInfo = hand.winner_info;
            const potAmount = winnerInfo?.pot_amount || parseFloat(hand.pot_amount) || 0;
            
            return {
              timestamp: new Date(hand.completed_at).getTime(),
              winners: winnerInfo?.winners || [],
              potAmount: potAmount,
              type: winnerInfo?.type || 'Unknown',
              handNumber: hand.hand_number
            };
          });
          setHandHistory(formattedHistory.slice(0, 5));
        }
      } catch (err) {
        // Silently fail polling errors to avoid spam
        console.warn('Polling update failed:', err);
      }
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, [id, game, showHandResults]);

  // Display temporary popup messages to user
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

  // Connect to WebSocket for real-time game updates
  const connectWebSocket = (gameId) => {
    // Check if WebSocket is supported
    if (!gameService.isWebSocketSupported()) {
      showMessage("Real-time updates not supported in this browser", "error");
      return;
    }

    setConnectionStatus("connecting");

    socketRef.current = gameService.connectToGameSocket(
      gameId,
      // onMessage
      (data) => {
        
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
                
                return { ...newPlayer, cards: existingPlayer.cards };
              }
              
              return newPlayer;
            });
          }
          
          // Check for hand completion and update history
          // Check if winner_info is present (hand just completed) or if hand_count increased (new hand started)
          const handJustCompleted = updatedGame.winner_info && (!currentGame.winner_info || 
              JSON.stringify(updatedGame.winner_info) !== JSON.stringify(currentGame.winner_info));
          
          const newHandStarted = updatedGame.hand_count > (currentGame.hand_count || 0);
          
          // If new hand started but we have winner_info from previous hand, show popup
          if ((handJustCompleted || newHandStarted) && updatedGame.winner_info) {
            console.log('🎯 Hand completion detected:', {
              handJustCompleted,
              newHandStarted,
              winnerInfo: updatedGame.winner_info,
              handCount: updatedGame.hand_count,
              currentShowingPopup: showHandResults
            });
            
            const winnerInfo = updatedGame.winner_info;
            
            const newHistoryEntry = {
              timestamp: Date.now(),
              winners: winnerInfo.winners || [],
              potAmount: winnerInfo.pot_amount || 0,
              type: winnerInfo.type || 'Unknown',
              handNumber: updatedGame.hand_count || currentGame.hand_count || 0,
              allPlayers: updatedGame.players || [] // Store all players for money change tracking
            };
            
            // Only show popup if we don't already have one showing for this hand
            if (!showHandResults || (currentHandResult && currentHandResult.handNumber !== newHistoryEntry.handNumber)) {
              console.log('✅ Showing hand results popup for hand #', newHistoryEntry.handNumber);
              setCurrentHandResult(newHistoryEntry);
              setShowHandResults(true);
              
              // Fetch fresh hand history from database after hand completion
              gameService.getHandHistory(gameId)
                .then(freshHistory => {
                  console.log('📜 Fetched fresh hand history:', freshHistory);
                  setHandHistory(freshHistory.slice(0, 5)); // Keep only last 5 hands
                })
                .catch(error => {
                  console.error('❌ Failed to fetch fresh hand history:', error);
                  // Fallback to WebSocket-based history update
                  setHandHistory(prevHistory => {
                    const existingIndex = prevHistory.findIndex(h => h.handNumber === newHistoryEntry.handNumber);
                    if (existingIndex === -1) {
                      const newHistory = [newHistoryEntry, ...prevHistory];
                      return newHistory.slice(0, 5);
                    }
                    return prevHistory;
                  });
                });
            } else {
              console.log('⏭️ Skipping popup - already showing for this hand');
            }
          }
          
          return updatedGame;
        });
        
        setConnectionStatus("connected");
        setError(null); // Clear any previous errors
        setMessage(null); // Clear any popup messages
      },
      // onError
      (errorMessage) => {
        setConnectionStatus("error");
        showMessage(`Connection error: ${errorMessage}`, "error");

        // Try to reconnect after 3 seconds
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket(gameId);
        }, 3000);
      },
      // onClose
      (event) => {
        setConnectionStatus("disconnected");

        // Only try to reconnect if it wasn't a normal closure or authentication issue
        if (event.code !== 1000 && event.code !== 4001 && event.code !== 4003) {

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

  // Start the poker game
  const handleStartGame = async () => {
    try {
      await gameService.startGame(id);
      // Game state will be updated via WebSocket
    } catch (err) {
      showMessage(err.response?.data?.error || "Failed to start game", "error");
    }
  };

  // Leave the poker game with confirmation dialog
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
      showMessage(err.response?.data?.error || "Failed to leave game", "error");
      
      // Even if the backend call fails, still navigate away after showing error
      // This ensures the player can always leave the UI even if there's a server issue
      setTimeout(() => {
        navigate("/tables");
      }, 2000);
    }
  };

  // Refresh game state from server
  const handleRefreshGame = async () => {
    try {
      const response = await gameService.resetGameState(id);
      setGame(response.data.game);
      showMessage("✅ Game state refreshed successfully", "success");
    } catch (err) {
      showMessage(
        `Failed to refresh game: ${err.response?.data?.error || err.message}`,
        "error"
      );
    }
  };

  // Handle player poker actions (fold, call, bet, raise, check)
  const handleAction = async (actionTypeParam = null, amountParam = null) => {
    try {
      const actionToUse = actionTypeParam || actionType;
      const amountToUse = amountParam !== null ? amountParam : betAmount;
      
      await gameService.takeAction(id, actionToUse, amountToUse);
      // Game state will be updated via WebSocket
      setError(null); // Clear any previous errors
      setMessage(null); // Clear any popup messages
    } catch (err) {
      showMessage(
        `${err.response?.data?.error || err.message}`,
        "error"
      );
    }
  };

  // Handle player ready for next hand
  const handlePlayerReady = async () => {
    try {
      await gameService.setPlayerReady(id);
      setShowHandResults(false);
      setCurrentHandResult(null);
      showMessage("✅ You're ready for the next hand!", "success", 2000);
    } catch (err) {
      showMessage(`Failed to set ready status: ${err.response?.data?.error || err.message}`, "error");
    }
  };

  // Handle cash out from game
  const handleCashOut = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to cash out and leave the game? Your remaining chips will be deposited to your account."
    );
    
    if (!confirmed) {
      return;
    }

    try {
      await gameService.cashOut(id);
      setShowHandResults(false);
      setCurrentHandResult(null);
      showMessage("💰 Cashed out successfully! Redirecting...", "success", 2000);
      
      // Redirect to tables after a short delay
      setTimeout(() => {
        navigate("/tables");
      }, 2000);
    } catch (err) {
      showMessage(`Failed to cash out: ${err.response?.data?.error || err.message}`, "error");
    }
  };

  // Render WebSocket connection status indicator
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

  // Get current user information from localStorage
  const getCurrentUserInfo = () => {
    try {
      const userStr = localStorage.getItem("user");
      if (userStr) {
        const user = JSON.parse(userStr);
        return user;
      }

      return null;
    } catch (e) {
      return null;
    }
  };

  // Find the current player in the game
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

  // Check if it's the current player's turn
  const isPlayerTurn = () => {
    const currentPlayer = findCurrentPlayer();
    return (
      currentPlayer &&
      game.current_player &&
      game.current_player.id === currentPlayer.player.id
    );
  };

  // Render game action buttons (fold, call, bet, raise, check)
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

  // Render all players around the poker table
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
        } else if (
          currentUser.username &&
          player.player.user.username === currentUser.username
        ) {
          isCurrentUser = true;
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

  // Render temporary popup messages to user
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

  // Render recent hand history
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
          {handHistory.map((hand, index) => {
            return (
              <div key={hand.timestamp} className="history-entry">
                <div className="entry-number">#{hand.handNumber || (handHistory.length - index)}</div>
                <div className="entry-details">
                  {hand.winners && hand.winners.length > 0 ? (
                    hand.winners.length === 1 ? (
                      <div className="winner-info">
                        <div className="winner-name">{hand.winners[0].player_name || 'Unknown Player'}</div>
                        <div className="winner-amount">
                          ${(hand.winners[0].winning_amount !== undefined && hand.winners[0].winning_amount !== null) 
                            ? Number(hand.winners[0].winning_amount).toFixed(2) 
                            : Number(hand.potAmount).toFixed(2)}
                        </div>
                      </div>
                    ) : (
                      <div className="winner-info">
                        <div className="winner-name">Split Pot ({hand.winners.length} winners)</div>
                        <div className="winner-amount">${Number(hand.potAmount).toFixed(2)}</div>
                      </div>
                    )
                  ) : (
                    <div className="winner-info">
                      <div className="winner-name">No Winner Info</div>
                      <div className="winner-amount">${Number(hand.potAmount).toFixed(2)}</div>
                    </div>
                  )}
                  {hand.winners && hand.winners[0] && hand.winners[0].hand_name && (
                    <div className="hand-type">{hand.winners[0].hand_name}</div>
                  )}
                  {hand.winners && hand.winners[0] && hand.winners[0].reason && (
                    <div className="hand-reason">{hand.winners[0].reason}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Render game information and controls
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

  // Render community cards on the table
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

  // Render recent game actions/logs
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

  // Render hand results popup
  const renderHandResultsPopup = () => {
    if (!showHandResults || !currentHandResult) {
      return null;
    }

    return (
      <div className="hand-results-overlay">
        <div className="hand-results-popup">
          <div className="hand-results-header">
            <h2>🎯 Hand #{currentHandResult.handNumber} Results</h2>
          </div>
          
          <div className="hand-results-content">
            <div className="pot-info">
              <div className="pot-amount">💰 Pot: ${Number(currentHandResult.potAmount).toFixed(2)}</div>
            </div>

            <div className="winners-section">
              <h3>🏆 Winner{currentHandResult.winners.length > 1 ? 's' : ''}</h3>
              {currentHandResult.winners.map((winner, index) => (
                <div key={index} className="winner-card">
                  <div className="winner-name">{winner.player_name}</div>
                  <div className="winner-amount">+${Number(winner.winning_amount).toFixed(2)}</div>
                  {winner.hand_name && (
                    <div className="winner-hand">{winner.hand_name}</div>
                  )}
                  {winner.reason && (
                    <div className="winner-reason">{winner.reason}</div>
                  )}
                  {winner.hole_cards && winner.hole_cards.length > 0 && (
                    <div className="winner-cards">
                      {winner.hole_cards.map((card, cardIndex) => {
                        const rank = card.slice(0, -1);
                        const suit = card.slice(-1);
                        const suitSymbols = { S: "♠", H: "♥", D: "♦", C: "♣" };
                        
                        return (
                          <div key={cardIndex} className="result-card" data-suit={suit}>
                            <div className="card-rank">{rank}</div>
                            <div className="card-suit">{suitSymbols[suit]}</div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Show money changes for other players */}
            {currentHandResult.winners && currentHandResult.winners.length > 0 && game.winner_info && game.winner_info.money_changes && (
              <div className="money-changes-section">
                <h3>💸 Money Changes</h3>
                <div className="money-changes-list">
                  {game.winner_info.money_changes.map(player => {
                    const isWinner = currentHandResult.winners.some(w => w.player_name === player.player_name);
                    if (isWinner) return null; // Winners already shown above
                    
                    return (
                      <div key={player.player_id} className="money-change-item loser">
                        <span className="player-name">{player.player_name}</span>
                        <span className="money-change">-${Number(player.total_bet_this_hand || 0).toFixed(2)}</span>
                      </div>
                    );
                  }).filter(Boolean)}
                </div>
              </div>
            )}
          </div>

          <div className="hand-results-footer">
            <div className="hand-results-buttons">
              <button 
                className="ready-btn"
                onClick={handlePlayerReady}
              >
                ✅ I'm Ready for Next Hand
              </button>
              <button 
                className="cash-out-btn"
                onClick={handleCashOut}
              >
                💰 Cash Out & Leave
              </button>
            </div>
            
            {/* Show readiness status if available */}
            {game && game.players && (
              <div className="readiness-status">
                <div className="status-text">
                  Waiting for all players to be ready...
                </div>
                <div className="players-ready">
                  {game.players.map(player => {
                    const isReady = player.ready_for_next_hand || false;
                    const isCurrentUser = getCurrentUserInfo() && 
                      (getCurrentUserInfo().id === player.player.user.id || 
                       getCurrentUserInfo().username === player.player.user.username);
                    
                    return (
                      <div key={player.id} className={`player-ready-indicator ${isReady ? 'ready' : 'not-ready'} ${isCurrentUser ? 'current-user' : ''}`}>
                        <span className="player-name">{player.player.user.username}</span>
                        <span className="ready-status">{isReady ? '✅' : '⏳'}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
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
      {renderHandResultsPopup()}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default PokerTable;
