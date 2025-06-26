// This file contains the API service for handling authentication, player, table, and game-related requests.
// It uses axios for HTTP requests and handles token management for authentication.
// It also includes a WebSocket connection for real-time game updates.
import axios from "axios";

const API_URL = "http://localhost:8000/api";

// Create axios instance with auth token handling
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor to attach auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle token refresh if access token expires
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem("refreshToken");
        const response = await axios.post(`${API_URL}/token/refresh/`, {
          refresh: refreshToken,
        });

        localStorage.setItem("accessToken", response.data.access);

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // If refresh fails, logout
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

const authService = {
  // Authenticate user with username and password
  login: async (username, password) => {
    const response = await axios.post(`${API_URL}/token/`, {
      username,
      password,
    });
    localStorage.setItem("accessToken", response.data.access);
    localStorage.setItem("refreshToken", response.data.refresh);
    return response.data;
  },

  // Log out user by removing stored tokens
  logout: () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
  },

  // Check if user is currently authenticated
  isAuthenticated: () => {
    return !!localStorage.getItem("accessToken");
  },
  
  // Check if current user has admin privileges
  isAdmin: () => {
    try {
      const userStr = localStorage.getItem("user");
      if (userStr) {
        const user = JSON.parse(userStr);
        return user.is_superuser || user.is_staff || user.username === 'admin';
      }
      return false;
    } catch (e) {
      return false;
    }
  },
};

const playerService = {
  // Get current player's profile information
  getProfile: () => apiClient.get(`/players/me/`),
  // Deposit money to player's account
  deposit: (amount) => apiClient.post(`/players/deposit/`, { amount }),
  // Withdraw money from player's account
  withdraw: (amount) => apiClient.post(`/players/withdraw/`, { amount }),
};

const tableService = {
  // Get all available poker tables
  getTables: () => apiClient.get(`/tables/`),
  // Get specific table details
  getTable: (id) => apiClient.get(`/tables/${id}/`),
  // Create a new poker table
  createTable: (tableData) => apiClient.post(`/tables/`, tableData),
  // Delete a specific table
  deleteTable: (id) => apiClient.delete(`/tables/${id}/`),
  // Delete all tables (admin only)
  deleteAllTables: () => apiClient.delete(`/tables/delete_all/`),
  // Join a table with specified buy-in amount
  joinTable: (id, buyIn) =>
    apiClient.post(`/tables/${id}/join_table/`, { buy_in: buyIn }),
};

// Updated sections for src/services/apiService.js

const gameService = {
  // Get all games
  getGames: () => apiClient.get(`/games/`),
  // Get specific game details
  getGame: (id) => apiClient.get(`/games/${id}/`),
  // Start a poker game
  startGame: (id) => apiClient.post(`/games/${id}/start/`),
  // Leave a poker table completely (only works if already cashed out)
  leaveGame: (id) => apiClient.post(`/games/${id}/leave/`),
  // Take a poker action (fold, check, call, bet, raise)
  takeAction: (id, actionType, amount = 0) =>
    apiClient.post(`/games/${id}/action/`, { action_type: actionType, amount }),
  
  // Set player ready for next hand
  setPlayerReady: (id) => apiClient.post(`/games/${id}/ready/`),
  
  // Cash out from active play (stay at table but become inactive)
  cashOut: (id) => apiClient.post(`/games/${id}/cash_out/`),
  
  // Buy back into the game after cashing out
  buyBackIn: (id, amount) => apiClient.post(`/games/${id}/buy_back_in/`, { amount }),
  
  // Reset game state when it gets corrupted
  resetGameState: (id) => apiClient.post(`/games/${id}/reset_game_state/`),
  
  // Admin only - delete game regardless of status
  deleteGame: (id) => apiClient.delete(`/games/${id}/`),

  // Connect to WebSocket for real-time game updates
  connectToGameSocket: (
    gameId,
    onMessageCallback,
    onErrorCallback = null,
    onCloseCallback = null
  ) => {
    const token = localStorage.getItem("accessToken");

    if (!token) {
      console.error("No access token found for WebSocket connection");
      if (onErrorCallback) onErrorCallback("No authentication token");
      return null;
    }

    // Construct WebSocket URL
    const wsUrl = `ws://localhost:8000/ws/game/${gameId}/?token=${token}`;
    console.log("Connecting to WebSocket:", wsUrl);

    try {
      const socket = new WebSocket(wsUrl);

      // Handle successful WebSocket connection
      socket.onopen = (event) => {
        console.log("WebSocket connected successfully to game", gameId);
      };

      // Handle incoming WebSocket messages
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("WebSocket message received:", data);
          onMessageCallback(data);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
          if (onErrorCallback) onErrorCallback("Failed to parse message");
        }
      };

      // Handle WebSocket errors
      socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        if (onErrorCallback) onErrorCallback("WebSocket connection error");
      };

      // Handle WebSocket connection close
      socket.onclose = (event) => {
        console.log("WebSocket closed:", event.code, event.reason);

        // Handle different close codes
        switch (event.code) {
          case 4001:
            console.error("WebSocket closed: Authentication failed");
            if (onErrorCallback) onErrorCallback("Authentication failed");
            break;
          case 4003:
            console.error("WebSocket closed: Permission denied");
            if (onErrorCallback) onErrorCallback("Permission denied");
            break;
          case 1006:
            console.error("WebSocket closed: Connection lost");
            if (onErrorCallback) onErrorCallback("Connection lost");
            break;
          default:
            console.log("WebSocket closed normally");
        }

        if (onCloseCallback) onCloseCallback(event);
      };

      return socket;
    } catch (error) {
      console.error("Error creating WebSocket:", error);
      if (onErrorCallback)
        onErrorCallback("Failed to create WebSocket connection");
      return null;
    }
  },

  // Check if WebSocket is supported by the browser
  isWebSocketSupported: () => {
    return "WebSocket" in window;
  },

  // Get hand history for a specific game
  getHandHistory: (gameId) => apiClient.get(`/games/${gameId}/hand-history/`),
};

export { authService, playerService, tableService, gameService };
