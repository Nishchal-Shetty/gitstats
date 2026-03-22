import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Home() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("repo"); // "repo" | "dev"
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    if (mode === "dev") {
      navigate(`/dev/${query.trim()}`);
    } else {
      const parts = query.trim().split("/");
      if (parts.length === 2) {
        navigate(`/repo/${parts[0]}/${parts[1]}`);
      }
    }
  };

  const loginWithGitHub = () => {
    const clientId = import.meta.env.VITE_GITHUB_CLIENT_ID;
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${clientId}&scope=read:user`;
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4">
      <h1 className="text-5xl font-bold mb-2 tracking-tight">
        Git<span className="text-indigo-400">Stats</span>
      </h1>
      <p className="text-gray-400 mb-10 text-lg">AI-powered GitHub repository analytics</p>

      <div className="w-full max-w-xl">
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setMode("repo")}
            className={`flex-1 py-2 rounded-lg font-medium transition ${
              mode === "repo"
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            Repository
          </button>
          <button
            onClick={() => setMode("dev")}
            className={`flex-1 py-2 rounded-lg font-medium transition ${
              mode === "dev"
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            Developer
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={mode === "repo" ? "owner/repo-name" : "github-username"}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg font-medium transition"
          >
            Analyze
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            onClick={loginWithGitHub}
            className="text-gray-400 hover:text-white text-sm underline underline-offset-2 transition"
          >
            Sign in with GitHub
          </button>
        </div>

        <div className="mt-8 text-center">
          <a
            href="/compare"
            className="text-indigo-400 hover:text-indigo-300 text-sm transition"
          >
            Compare repositories →
          </a>
        </div>
      </div>
    </div>
  );
}
