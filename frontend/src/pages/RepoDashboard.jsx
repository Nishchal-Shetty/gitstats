import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import StatCard from "../components/StatCard";
import GenreTag from "../components/GenreTag";
import RepoChart from "../components/RepoChart";
import SimilarRepos from "../components/SimilarRepos";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function RepoDashboard() {
  const { owner, repo } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    axios
      .get(`${API}/repo/${owner}/${repo}`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load repo"))
      .finally(() => setLoading(false));
  }, [owner, repo]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-400 animate-pulse text-lg">Analyzing {owner}/{repo}...</div>
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

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="mb-6">
        <a href="/" className="text-gray-500 hover:text-white text-sm transition">← Back</a>
      </div>

      <div className="flex items-start justify-between mb-2">
        <div>
          <h1 className="text-3xl font-bold">{data.full_name}</h1>
          {data.description && (
            <p className="text-gray-400 mt-1">{data.description}</p>
          )}
        </div>
        {data.genre && <GenreTag genre={data.genre} />}
      </div>

      <div className="flex flex-wrap gap-2 mt-3 mb-8">
        {data.tags?.map((tag) => (
          <span key={tag} className="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded-full">
            {tag}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Stars" value={data.stars?.toLocaleString()} icon="★" />
        <StatCard label="Forks" value={data.forks?.toLocaleString()} icon="⑂" />
        <StatCard label="Open Issues" value={data.open_issues?.toLocaleString()} icon="!" />
        <StatCard label="Watchers" value={data.watchers?.toLocaleString()} icon="👁" />
      </div>

      {data.readme_summary && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
          <h2 className="text-lg font-semibold mb-2">AI Summary</h2>
          <p className="text-gray-300 leading-relaxed">{data.readme_summary}</p>
        </div>
      )}

      <RepoChart repo={data} />
      <SimilarRepos genre={data.genre} currentRepo={data.full_name} />
    </div>
  );
}
