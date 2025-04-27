// This file contains the API service for handling authentication, player, table, and game-related requests.
// It uses axios for HTTP requests and handles token management for authentication.
// It also includes a WebSocket connection for real-time game updates.
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

// Create axios instance with auth token handling
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to attach auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
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
        const refreshToken = localStorage.getItem('refreshToken');
        const response = await axios.post(`${API_URL}/token/refresh/`, { refresh: refreshToken });
        
        localStorage.setItem('accessToken', response.data.access);
        
        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // If refresh fails, logout
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

const authService = {
  login: async (username, password) => {
    const response = await axios.post(`${API_URL}/token/`, { username, password });
    localStorage.setItem('accessToken', response.data.access);
    localStorage.setItem('refreshToken', response.data.refresh);
    return response.data;
  },
  
  logout: () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
  },
  
  isAuthenticated: () => {
    return !!localStorage.getItem('accessToken');
  }
};

const playerService = {
  getProfile: () => apiClient.get(`/players/me/`),
  deposit: (amount) => apiClient.post(`/players/deposit/`, { amount }),
  withdraw: (amount) => apiClient.post(`/players/withdraw/`, { amount }),
};

const tableService = {
  getTables: () => apiClient.get(`/tables/`),
  getTable: (id) => apiClient.get(`/tables/${id}/`),
  createTable: (tableData) => apiClient.post(`/tables/`, tableData),
  joinTable: (id, buyIn) => apiClient.post(`/tables/${id}/join_table/`, { buy_in: buyIn }),
};

const gameService = {
  getGames: () => apiClient.get(`/games/`),
  getGame: (id) => apiClient.get(`/games/${id}/`),
  startGame: (id) => apiClient.post(`/games/${id}/start/`),
  leaveGame: (id) => apiClient.post(`/games/${id}/leave/`),
  takeAction: (id, actionType, amount = 0) => 
    apiClient.post(`/games/${id}/action/`, { action_type: actionType, amount }),
  
  // WebSocket connection for real-time updates
  connectToGameSocket: (gameId, onMessageCallback) => {
    const token = localStorage.getItem('accessToken');
    const socket = new WebSocket(`ws://localhost:8000/ws/game/${gameId}/?token=${token}`);
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessageCallback(data);
    };
    
    return socket;
  }
};

export { authService, playerService, tableService, gameService };