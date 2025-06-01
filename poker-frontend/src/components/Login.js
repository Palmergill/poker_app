// src/components/Login.js
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authService, playerService } from "../services/apiService";

const Login = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // First, login to get tokens
      const response = await authService.login(username, password);

      // After successful login, get the user's full profile
      try {
        const profileResponse = await playerService.getProfile();

        // Store complete user info with proper structure
        const userInfo = {
          id: profileResponse.data.user.id,
          username: profileResponse.data.user.username,
          email: profileResponse.data.user.email,
          playerId: profileResponse.data.id,
        };

        localStorage.setItem("user", JSON.stringify(userInfo));
        console.log("User info stored:", userInfo);
      } catch (profileError) {
        console.error("Failed to get profile, using basic info:", profileError);

        // Fallback: store basic user info if profile fetch fails
        const basicUserInfo = {
          username: username,
          // The backend might return user_id in the token response
          id: response.user_id || null,
        };

        localStorage.setItem("user", JSON.stringify(basicUserInfo));
      }

      navigate("/tables");
    } catch (err) {
      console.error("Login error:", err);
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-form">
      <h2>Login to Poker App</h2>
      {error && <div className="error-message">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>

      <p>
        Don't have an account? <a href="/register">Register</a>
      </p>
    </div>
  );
};

export default Login;
