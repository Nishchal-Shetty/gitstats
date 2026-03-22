import { Routes, Route, Link, NavLink } from "react-router-dom";
import Home from "./pages/Home";
import RepoDashboard from "./pages/RepoDashboard";
import DevDashboard from "./pages/DevDashboard";
import Compare from "./pages/Compare";

function Navbar() {
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
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <div className="min-h-screen text-gray-100" style={{ backgroundColor: "#0d1117" }}>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/repo/:owner/:repo" element={<RepoDashboard />} />
        <Route path="/dev/:username" element={<DevDashboard />} />
        <Route path="/compare" element={<Compare />} />
      </Routes>
    </div>
  );
}
