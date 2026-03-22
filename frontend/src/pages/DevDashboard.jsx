import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import StatCard from "../components/StatCard";
import GenreTag from "../components/GenreTag";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function DevDashboard() {
  const { username } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    axios
      .get(`${API}/dev/${username}`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load developer"))
      .finally(() => setLoading(false));
  }, [username]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-400 animate-pulse text-lg">Loading {username}'s profile...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-400">{error}</div>
      </div>
    );
  }

  const languageCounts = data.repos.reduce((acc, repo) => {
    if (repo.language) acc[repo.language] = (acc[repo.language] || 0) + 1;
    return acc;
  }, {});

  const topLanguages = Object.entries(languageCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="mb-6">
        <a href="/" className="text-gray-500 hover:text-white text-sm transition">← Back</a>
      </div>

      <h1 className="text-3xl font-bold mb-1">{username}</h1>

      {data.summary && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8 mt-4">
          <h2 className="text-lg font-semibold mb-2">AI Developer Profile</h2>
          <p className="text-gray-300 leading-relaxed">{data.summary}</p>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <StatCard label="Public Repos" value={data.total_repos} icon="📦" />
        <StatCard label="Total Stars" value={data.total_stars?.toLocaleString()} icon="★" />
        <StatCard label="Top Language" value={topLanguages[0]?.[0] || "N/A"} icon="⌨" />
      </div>

      {topLanguages.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3">Languages</h2>
          <div className="flex flex-wrap gap-2">
            {topLanguages.map(([lang, count]) => (
              <span key={lang} className="bg-gray-800 text-gray-300 text-sm px-3 py-1 rounded-full">
                {lang} <span className="text-gray-500">({count})</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <h2 className="text-lg font-semibold mb-3">Repositories</h2>
      <div className="grid gap-3">
        {data.repos.map((repo) => (
          <Link
            key={repo.full_name}
            to={`/repo/${repo.full_name}`}
            className="bg-gray-900 border border-gray-800 hover:border-indigo-600 rounded-xl p-4 transition block"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="font-medium text-white">{repo.name}</div>
                {repo.description && (
                  <div className="text-gray-400 text-sm mt-0.5 line-clamp-1">{repo.description}</div>
                )}
                <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
                  {repo.language && <span>{repo.language}</span>}
                  <span>★ {repo.stars}</span>
                  <span>⑂ {repo.forks}</span>
                </div>
              </div>
              {repo.genre && <GenreTag genre={repo.genre} small />}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
