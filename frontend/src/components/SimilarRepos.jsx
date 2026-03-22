import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function SimilarRepos({ genre, currentRepo }) {
  const [repos, setRepos] = useState([]);

  useEffect(() => {
    if (!genre) return;
    axios
      .get(`${API}/search`, { params: { q: genre } })
      .then((res) => setRepos(res.data.filter((r) => r.full_name !== currentRepo).slice(0, 5)))
      .catch(() => {});
  }, [genre, currentRepo]);

  if (!repos.length) return null;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold mb-4">Similar Repositories</h2>
      <div className="flex flex-col gap-3">
        {repos.map((repo) => (
          <Link
            key={repo.full_name}
            to={`/repo/${repo.full_name}`}
            className="flex items-center justify-between hover:text-indigo-400 transition"
          >
            <div>
              <div className="text-white font-medium">{repo.full_name}</div>
              {repo.description && (
                <div className="text-gray-500 text-sm line-clamp-1">{repo.description}</div>
              )}
            </div>
            <div className="text-gray-400 text-sm ml-4 whitespace-nowrap">★ {repo.stars?.toLocaleString()}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
