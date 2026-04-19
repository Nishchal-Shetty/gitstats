import { Routes, Route, Link, NavLink } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Home from "./pages/Home";
import RepoDashboard from "./pages/RepoDashboard";
import DevDashboard from "./pages/DevDashboard";
import Compare from "./pages/Compare";
import AuthCallback from "./pages/AuthCallback";
import Recommendations from "./pages/Recommendations";
import Analytics from "./pages/Analytics";

const GITHUB_CLIENT_ID = import.meta.env.VITE_GITHUB_CLIENT_ID;

function LoginButton() {
  const redirectUri = `${window.location.origin}/auth/callback`;
  const githubUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&scope=read:user user:email`;

  return (
    <a
      href={githubUrl}
      className="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-md border border-gray-600 text-gray-300 hover:text-white hover:border-gray-400 transition"
    >
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
      </svg>
      Sign in
    </a>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();

  return (
    <div className="flex items-center gap-3">
      <img
        src={user.avatar_url}
        alt={user.username}
        className="w-7 h-7 rounded-full border border-gray-600"
      />
      <span className="text-sm text-gray-300 hidden sm:inline">{user.username}</span>
      <button
        onClick={logout}
        className="text-xs text-gray-500 hover:text-gray-300 transition"
      >
        Sign out
      </button>
    </div>
  );
}

function Navbar() {
  const { user, loading } = useAuth();

  return (
    <nav style={{ backgroundColor: "#0d1117" }} className="border-b border-gray-800">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="text-white font-bold text-lg tracking-tight">
          Git<span className="text-indigo-400">Stats</span>
        </Link>
        <div className="flex items-center gap-6">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `text-sm transition ${isActive ? "text-white" : "text-gray-400 hover:text-white"}`
            }
          >
            Home
          </NavLink>
          <NavLink
            to="/compare"
            className={({ isActive }) =>
              `text-sm transition ${isActive ? "text-white" : "text-gray-400 hover:text-white"}`
            }
          >
            Compare
          </NavLink>
          <NavLink
            to="/recommendations"
            className={({ isActive }) =>
              `text-sm transition ${isActive ? "text-white" : "text-gray-400 hover:text-white"}`
            }
          >
            Recommendations
          </NavLink>
          <NavLink 
            to="/analytics"
            className={({ isActive }) =>
              `text-sm transition ${isActive ? "text-white" : "text-gray-400 hover:text-white"}`
            }
          >
            Analytics
          </NavLink>
          {!loading && (user ? <UserMenu /> : <LoginButton />)}
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen text-gray-100" style={{ backgroundColor: "#0d1117" }}>
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/repo/:owner/:repo" element={<RepoDashboard />} />
          <Route path="/dev/:username" element={<DevDashboard />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
      </div>
    </AuthProvider>
  );
}
