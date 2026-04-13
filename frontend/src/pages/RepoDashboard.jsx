import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import {
  BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import StatCard from "../components/StatCard";
import GenreTag from "../components/GenreTag";
import SimilarRepos from "../components/SimilarRepos";

const API = "/api";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-md border border-gray-700 px-3 py-2 text-xs"
      style={{ backgroundColor: "#161b22" }}
    >
      <div className="text-gray-300 font-medium mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.fill }}>
          {p.name}: {Number(p.value).toLocaleString()}
        </div>
      ))}
    </div>
  );
}

export default function RepoDashboard() {
  const { owner, repo } = useParams();
  const [data, setData] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    setSimilar([]);

    axios
      .get(`${API}/stats/repo/${owner}/${repo}`)
      .then((res) => {
        console.log("API response /stats/repo:", res.data);
        setData(res.data);
        return axios
          .get(`${API}/repos/similar/${owner}/${repo}`)
          .catch((err) => {
            console.warn("Similar repos fetch failed:", err.response?.data ?? err.message);
            return { data: [] };
          });
      })
      .then((res) => {
        console.log("API response /repos/similar:", res.data);
        setSimilar(res.data ?? []);
      })
      .catch((err) => setError(err.response?.data?.detail || "Failed to load repository"))
      .finally(() => setLoading(false));
  }, [owner, repo]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <div className="text-gray-400 text-sm">Fetching {owner}/{repo}…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <div className="text-red-400 mb-4">{error}</div>
        <Link to="/" className="text-indigo-400 text-sm hover:underline">← Back to home</Link>
      </div>
    );
  }

  // genre_comparison keys: avg_stars, avg_forks, avg_issues, total_in_genre, genre
  const cmp = data.genre_comparison ?? {};
  const avgStars  = cmp.avg_stars  ?? null;
  const avgForks  = cmp.avg_forks  ?? null;
  const avgIssues = cmp.avg_issues ?? null;

  const chartData = [
    { metric: "Stars",       "This repo": data.stars,       "Genre avg": Math.round(avgStars  ?? 0) },
    { metric: "Forks",       "This repo": data.forks,       "Genre avg": Math.round(avgForks  ?? 0) },
    { metric: "Open Issues", "This repo": data.open_issues, "Genre avg": Math.round(avgIssues ?? 0) },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">{data.full_name}</h1>
        {data.description && (
          <p className="text-gray-400 text-sm mb-3">{data.description}</p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {data.genre && data.genre !== "unknown" && (
            <GenreTag genre={data.genre} confidence={data.confidence} />
          )}
          {data.language && (
            <span className="text-xs text-gray-500 border border-gray-700 rounded px-2 py-0.5">
              {data.language}
            </span>
          )}
          {data.tags?.map((tag) => (
            <span key={tag} className="text-xs text-gray-500 border border-gray-700 rounded px-2 py-0.5">
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Stat cards */}
      <div className="flex flex-col sm:flex-row gap-3 mb-10">
        <StatCard title="Stars"       value={data.stars}       average={avgStars}  icon="★" />
        <StatCard title="Forks"       value={data.forks}       average={avgForks}  icon="⑂" />
        <StatCard title="Open Issues" value={data.open_issues} average={avgIssues} icon="!" />
        {data.contributor_count > 0 && (
          <StatCard title="Contributors" value={data.contributor_count} average={null} icon="👥" />
        )}
      </div>

      {/* 3 separate bar charts — one per metric so each has its own scale */}
      {cmp.total_in_genre > 1 ? (
        <div
          className="rounded-lg border border-gray-700 p-5 mb-10"
          style={{ backgroundColor: "#161b22" }}
        >
          <h2 className="text-sm font-semibold text-white mb-1">
            vs. {cmp.genre?.replace(/_/g, " ")} average
          </h2>
          <p className="text-xs text-gray-500 mb-5">
            Based on {cmp.total_in_genre} repos in this genre
          </p>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Stars",       repoVal: data.stars,       avg: Math.round(avgStars  ?? 0) },
              { label: "Forks",       repoVal: data.forks,       avg: Math.round(avgForks  ?? 0) },
              { label: "Open Issues", repoVal: data.open_issues, avg: Math.round(avgIssues ?? 0) },
            ].map(({ label, repoVal, avg }) => (
              <div key={label}>
                <div className="text-xs text-gray-500 text-center mb-2">{label}</div>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart
                    data={[
                      { name: "This repo", value: repoVal },
                      { name: "Genre avg", value: avg },
                    ]}
                    barCategoryGap="25%"
                  >
                    <XAxis dataKey="name" tick={{ fill: "#8b949e", fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis
                      tick={{ fill: "#8b949e", fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                      width={40}
                      tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                    <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                      <Cell fill="#388bfd" />
                      <Cell fill="#30363d" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-xs text-gray-600 mb-10">
          Genre comparison charts will appear once more repos in this genre are scraped
          (current count: {cmp.total_in_genre ?? 0}).
        </div>
      )}

      {/* Similar repos */}
      {similar.length > 0
        ? <SimilarRepos repos={similar} />
        : <p className="text-xs text-gray-600">No similar repos found yet — try scraping more repos in this genre.</p>
      }
    </div>
  );
}
