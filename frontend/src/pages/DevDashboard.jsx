import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const LANG_COLORS = [
  "#388bfd", "#56d364", "#d2a8ff", "#ffa657", "#ff7b72",
  "#79c0ff", "#e3b341", "#39d3c3", "#f778ba", "#8b949e",
];

function PieTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-md border border-gray-700 px-3 py-2 text-xs"
      style={{ backgroundColor: "#161b22" }}
    >
      <span style={{ color: payload[0].payload.fill }}>{payload[0].name}</span>
      <span className="text-gray-400 ml-2">{payload[0].payload.pct}%</span>
    </div>
  );
}

function RepoCard({ repo }) {
  const [owner, name] = repo.full_name.split("/");
  return (
    <Link
      to={`/repo/${owner}/${name}`}
      className="block rounded-lg border border-gray-700 p-4 hover:border-gray-500 transition"
      style={{ backgroundColor: "#161b22" }}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-sm font-semibold text-white truncate">{name}</span>
        <span className="text-xs text-yellow-400 shrink-0">★ {repo.stars?.toLocaleString()}</span>
      </div>
      {repo.description && (
        <p className="text-xs text-gray-400 line-clamp-2 mb-3">{repo.description}</p>
      )}
      {repo.language && (
        <span className="text-xs text-gray-500 border border-gray-700 rounded px-2 py-0.5">
          {repo.language}
        </span>
      )}
    </Link>
  );
}

function StatPill({ label, value }) {
  return (
    <span
      className="inline-flex items-center gap-1 text-xs rounded-full px-3 py-1 border border-gray-700"
      style={{ backgroundColor: "#21262d" }}
    >
      <span className="text-white font-semibold">{value?.toLocaleString()}</span>
      <span className="text-gray-500">{label}</span>
    </span>
  );
}

export default function DevDashboard() {
  const { username } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    axios
      .get(`${API}/stats/developer/${username}`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Could not load developer profile."))
      .finally(() => setLoading(false));
  }, [username]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <div className="text-gray-400 text-sm">Loading {username}'s profile…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <div className="text-red-400 mb-2">Failed to load developer</div>
        <div className="text-gray-500 text-sm mb-6">{error}</div>
        <Link to="/" className="text-indigo-400 text-sm hover:underline">← Back to home</Link>
      </div>
    );
  }

  // Build pie data from top_languages — equal slice weight, labeled with %
  const total = data.top_languages?.length || 1;
  const pieData = (data.top_languages ?? []).map((lang, i) => ({
    name: lang,
    value: 1,
    pct: Math.round((1 / total) * 100),
    fill: LANG_COLORS[i % LANG_COLORS.length],
  }));

  const topRepos = (data.top_repos ?? []).slice(0, 6);

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">

      {/* Header */}
      <div
        className="rounded-lg border border-gray-700 p-6 mb-8 flex flex-col sm:flex-row items-start gap-5"
        style={{ backgroundColor: "#161b22" }}
      >
        {data.avatar_url && (
          <img
            src={data.avatar_url}
            alt={data.github_username}
            className="w-20 h-20 rounded-full border-2 border-gray-600 shrink-0"
          />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-white">
              {data.display_name || data.github_username}
            </h1>
            {data.display_name && (
              <span className="text-gray-500 text-sm">@{data.github_username}</span>
            )}
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            <StatPill label="followers"    value={data.followers} />
            <StatPill label="following"    value={data.following} />
            <StatPill label="public repos" value={data.public_repos} />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold" style={{ color: "#56d364" }}>
              ★ {data.total_stars?.toLocaleString()}
            </span>
            <span className="text-sm text-gray-500">total stars</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-10">
        {/* Pie chart */}
        {pieData.length > 0 && (
          <div
            className="rounded-lg border border-gray-700 p-5"
            style={{ backgroundColor: "#161b22" }}
          >
            <h2 className="text-sm font-semibold text-white mb-4">Top Languages</h2>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, pct }) => `${name} ${pct}%`}
                  labelLine={{ stroke: "#374151" }}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Quick stats */}
        <div className="flex flex-col gap-3 justify-center">
          {[
            { label: "Public Repositories", value: data.public_repos },
            { label: "Followers",           value: data.followers },
            { label: "Following",           value: data.following },
            { label: "Total Stars Earned",  value: data.total_stars },
          ].map(({ label, value }) => (
            <div
              key={label}
              className="flex items-center justify-between rounded-lg border border-gray-700 px-4 py-3"
              style={{ backgroundColor: "#161b22" }}
            >
              <span className="text-sm text-gray-400">{label}</span>
              <span className="text-sm font-semibold text-white">{value?.toLocaleString() ?? "—"}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top repos */}
      {topRepos.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-white mb-4">Top Repositories</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {topRepos.map((repo) => (
              <RepoCard key={repo.full_name} repo={repo} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
