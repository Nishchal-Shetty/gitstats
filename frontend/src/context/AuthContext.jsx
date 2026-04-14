import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // On mount, restore session from localStorage
  useEffect(() => {
    const savedToken = localStorage.getItem("gitstats_token");
    const savedUser = localStorage.getItem("gitstats_user");
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  // Exchange GitHub OAuth code for JWT + user
  const login = async (code) => {
    const res = await axios.post(`${API}/auth/github`, { code });
    const { token: jwt, user: userData } = res.data;
    setToken(jwt);
    setUser(userData);
    localStorage.setItem("gitstats_token", jwt);
    localStorage.setItem("gitstats_user", JSON.stringify(userData));
    return userData;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("gitstats_token");
    localStorage.removeItem("gitstats_user");
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === null) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
