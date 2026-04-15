import React, { useState } from "react";
import { login, signup } from "../api";

export default function AuthPanel({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function getApiErrorMessage(err) {
    if (err?.code === "ERR_NETWORK") {
      return "Backend is not reachable. Please try again in a moment.";
    }

    const responseData = err?.response?.data;
    if (!responseData) {
      return "Authentication failed";
    }

    if (typeof responseData.detail === "string") {
      return responseData.detail;
    }

    if (Array.isArray(responseData.errors) && responseData.errors.length > 0) {
      const first = responseData.errors[0];
      const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : "field";
      if (field === "username" && String(first?.msg || "").toLowerCase().includes("pattern")) {
        return "Username can use letters, numbers, and underscore only.";
      }
      if (field === "password" && String(first?.msg || "").toLowerCase().includes("least")) {
        return "Password must be at least 8 characters.";
      }
      return `${field}: ${first?.msg || "Invalid value"}`;
    }

    return "Authentication failed";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const normalizedUsername = username.trim();
      const normalizedEmail = email.trim();
      const normalizedPassword = password;

      if (mode === "signup") {
        if (normalizedUsername.includes("@")) {
          setError("Use a username in the first field. Put your email in the Email field.");
          return;
        }
        await signup({
          username: normalizedUsername,
          email: normalizedEmail,
          password: normalizedPassword
        });
      }

      const auth = await login({ username: normalizedUsername, password: normalizedPassword });
      localStorage.setItem("auth_token", auth.access_token);
      onAuthenticated?.();
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-layout">
      <div className="auth-intro">
        <p className="auth-tag">Stock Whisperer</p>
        <h2>Quietly read the tape before the crowd</h2>
        <p>
          Sign in to sync your watchlist with live quotes, automate price alerts, and run the
          hybrid forecast stack for NSE and BSE symbols.
        </p>

        <div className="auth-highlights">
          <div>
            <strong>Live watchlist quotes</strong>
            <span>Server-side batch quotes for everything you track</span>
          </div>
          <div>
            <strong>Smart alerts</strong>
            <span>Above or below targets with background price checks</span>
          </div>
          <div>
            <strong>Forecast + sentiment</strong>
            <span>1d / 3d / 7d horizons with headline-aware suggestions</span>
          </div>
        </div>
      </div>

      <div className="auth-card-pro">
        <div className="auth-mode-switch" role="tablist" aria-label="Authentication mode">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === "signup" ? "active" : ""}
            onClick={() => setMode("signup")}
          >
            Sign Up
          </button>
        </div>

        <h3>{mode === "login" ? "Welcome back" : "Create your account"}</h3>
        <p className="auth-muted">
          {mode === "login"
            ? "Use your username or email and password to continue."
            : "Start your stock workspace in less than a minute."}
        </p>

        <form onSubmit={handleSubmit} className="auth-form auth-form-pro">
          <label>
            {mode === "login" ? "Username or Email" : "Username"}
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder={mode === "login" ? "e.g. parth01 or parth@example.com" : "e.g. parth01"}
              required
            />
          </label>

          {mode === "signup" ? (
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
          ) : null}

          <label>
            Password
            <div className="password-wrap">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((prev) => !prev)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>

          {error ? <p className="live-error">{error}</p> : null}

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Login to Dashboard"
                : "Create Account"}
          </button>
        </form>

        <p className="auth-switch">
          {mode === "login" ? "New user?" : "Already have an account?"}{" "}
          <button
            type="button"
            className="link-btn"
            onClick={() => setMode(mode === "login" ? "signup" : "login")}
          >
            {mode === "login" ? "Create account" : "Login"}
          </button>
        </p>
      </div>
    </section>
  );
}
