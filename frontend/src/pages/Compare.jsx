import { useState } from "react";
import axios from "axios";
import StatCard from "../components/StatCard";
import GenreTag from "../components/GenreTag";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Compare() {
  const [inputs, setInputs] = useState(["", ""]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCompare = async (e) => {
    e.preventDefault();
    const valid = inputs.filter((i) => i.trim());
    if (valid.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/compare`, {
        params: { repos: valid.join(",") },
      });
      setResults(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const addInput = () => setInputs((prev) => [...prev, ""]);
  const updateInput = (i, val) => setInputs((prev) => prev.map((v, idx) => (idx === i ? val : v)));

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="mb-6">
        <a href="/" className="text-gray-500 hover:text-white text-sm transition">← Back</a>
      </div>

      <h1 className="text-3xl font-bold mb-6">Compare Repositories</h1>

      <form onSubmit={handleCompare} className="mb-8">
        <div className="flex flex-col gap-2 mb-4">
          {inputs.map((val, i) => (
            <input
              key={i}
              type="text"
              value={val}
              onChange={(e) => updateInput(i, e.target.value)}
              placeholder={`owner/repo-name`}
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            />
          ))}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={addInput}
            className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm transition"
          >
            + Add repo
          </button>
          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg font-medium transition disabled:opacity-50"
          >
            {loading ? "Comparing..." : "Compare"}
          </button>
        </div>
      </form>

      {error && <div className="text-red-400 mb-6">{error}</div>}

      {results.length > 0 && (
        <div className="grid md:grid-cols-2 gap-6">
          {results.map((repo) => (
            <div key={repo.full_name} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              {repo.error ? (
                <div>
                  <div className="font-medium text-white mb-1">{repo.full_name}</div>
                  <div className="text-red-400 text-sm">{repo.error}</div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="font-semibold text-white">{repo.full_name}</div>
                      {repo.description && (
                        <div className="text-gray-400 text-sm mt-0.5 line-clamp-2">{repo.description}</div>
                      )}
                    </div>
                    {repo.genre && <GenreTag genre={repo.genre} small />}
                  </div>
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <StatCard label="Stars" value={repo.stars?.toLocaleString()} icon="★" small />
                    <StatCard label="Forks" value={repo.forks?.toLocaleString()} icon="⑂" small />
                    <StatCard label="Issues" value={repo.open_issues?.toLocaleString()} icon="!" small />
                    <StatCard label="Watchers" value={repo.watchers?.toLocaleString()} icon="👁" small />
                  </div>
                  {repo.readme_summary && (
                    <p className="text-gray-400 text-sm leading-relaxed">{repo.readme_summary}</p>
                  )}
                  <div className="flex flex-wrap gap-1 mt-3">
                    {repo.tags?.map((tag) => (
                      <span key={tag} className="bg-gray-800 text-gray-400 text-xs px-2 py-0.5 rounded-full">
                        {tag}
                      </span>
                    ))}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
