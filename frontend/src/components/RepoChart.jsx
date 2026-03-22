import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

export default function RepoChart({ repo }) {
  const max = Math.max(repo.stars, repo.forks, repo.open_issues, repo.watchers, 1);

  const data = [
    { metric: "Stars", value: Math.round((repo.stars / max) * 100) },
    { metric: "Forks", value: Math.round((repo.forks / max) * 100) },
    { metric: "Issues", value: Math.round((repo.open_issues / max) * 100) },
    { metric: "Watchers", value: Math.round((repo.watchers / max) * 100) },
  ];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
      <h2 className="text-lg font-semibold mb-4">Activity Radar</h2>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data}>
          <PolarGrid stroke="#374151" />
          <PolarAngleAxis dataKey="metric" tick={{ fill: "#9ca3af", fontSize: 13 }} />
          <Radar
            dataKey="value"
            stroke="#6366f1"
            fill="#6366f1"
            fillOpacity={0.25}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            labelStyle={{ color: "#e5e7eb" }}
            itemStyle={{ color: "#a5b4fc" }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
