import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import RepoDashboard from "./pages/RepoDashboard";
import DevDashboard from "./pages/DevDashboard";
import Compare from "./pages/Compare";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/repo/:owner/:repo" element={<RepoDashboard />} />
        <Route path="/dev/:username" element={<DevDashboard />} />
        <Route path="/compare" element={<Compare />} />
      </Routes>
    </div>
  );
}
