import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import {
  BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import GenreTag from "../components/GenreTag";

const API = import.meta.env.VITE_API_URL;

const COLOR_A = "#388bfd";
const COLOR_B = "#ffa657";

function RepoInput({ label, owner, repo, onOwner, onRepo }) {
  return (
    <div
      className="flex-1 rounded-lg border border-gray-700 p-5"
      style={{ backgroundColor: "#161b22" }}
    >
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">{label}</div>
      <div className="flex flex-col gap-2">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Owner</label>
          <input
            type="text"
            value={owner}
            onChange={(e) => onOwner(e.target.value)}
            placeholder="e.g. facebook"
            className="w-full rounded-md border border-gray-600 bg-gray-900 text-white placeholder-gray-600 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Repository</label>
          <input
            type="text"
            value={repo}
            onChange={(e) => onRepo(e.target.value)}
            placeholder="e.g. react"
            className="w-full rounded-md border border-gray-600 bg-gray-900 text-white placeholder-gray-600 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>
    </div>
  );
}

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

// Returns "a" | "b" | "tie" for numeric comparison. lowerWins flips the logic.
function winner(a, b, lowerWins = false) {
  if (a == null || b == null) return "tie";
  if (a === b) return "tie";
  if (lowerWins) return a < b ? "a" : "b";
  return a > b ? "a" : "b";
}

function Cell_({ value, win, side }) {
  const isWinner = win === side;
  return (
    <td className="px-4 py-3 text-sm text-center" style={{ color: isWinner ? "#56d364" : "#e6edf3" }}>
      {value ?? "—"}
      {isWinner && <span className="ml-1 text-xs">▲</span>}
    </td>
  );
}

function TagList({ tags }) {
  if (!tags?.length) return <span className="text-gray-600 text-xs">none</span>;
  return (
    <div className="flex flex-wrap gap-1 justify-center">
      {tags.map((t) => (
        <span key={t} className="text-xs border border-gray-700 rounded px-1.5 py-0.5 text-gray-400">{t}</span>
      ))}
    </div>
  );
}

export default function Compare() {
  const [ownerA, setOwnerA] = useState("");
  const [repoA, setRepoA]   = useState("");
  const [ownerB, setOwnerB] = useState("");
  const [repoB, setRepoB]   = useState("");

  const [results, setResults] = useState(null);   // [dataA, dataB] | null
  const [errors, setErrors]   = useState([null, null]);
  const [loading, setLoading] = useState(false);

  const canSubmit = ownerA.trim() && repoA.trim() && ownerB.trim() && repoB.trim();

  const handleCompare = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setResults(null);
    setErrors([null, null]);

    const fetch = (o, r) =>
      axios
        .get(`${API}/stats/repo/${o.trim()}/${r.trim()}`)
        .then((res) => ({ data: res.data, error: null }))
        .catch((err) => ({ data: null, error: err.response?.data?.detail || "Failed to load" }));

    const [a, b] = await Promise.all([fetch(ownerA, repoA), fetch(ownerB, repoB)]);
    setErrors([a.error, b.error]);
    if (a.data && b.data) setResults([a.data, b.data]);
    else if (a.data || b.data) setResults([a.data, b.data]); // partial — still render what we have
    setLoading(false);
  };

  const [dA, dB] = results ?? [null, null];

  const chartData = dA && dB
    ? [
        { metric: "Stars",       [dA.full_name]: dA.stars,       [dB.full_name]: dB.stars },
        { metric: "Forks",       [dA.full_name]: dA.forks,       [dB.full_name]: dB.forks },
        { metric: "Open Issues", [dA.full_name]: dA.open_issues, [dB.full_name]: dB.open_issues },
      ]
    : [];

  const rows = dA && dB
    ? [
        { label: "Stars",       vA: dA.stars?.toLocaleString(),       vB: dB.stars?.toLocaleString(),       win: winner(dA.stars, dB.stars) },
        { label: "Forks",       vA: dA.forks?.toLocaleString(),       vB: dB.forks?.toLocaleString(),       win: winner(dA.forks, dB.forks) },
        { label: "Open Issues", vA: dA.open_issues?.toLocaleString(), vB: dB.open_issues?.toLocaleString(), win: winner(dA.open_issues, dB.open_issues, true) },
        ...((dA.contributor_count || dB.contributor_count)
          ? [{ label: "Contributors", vA: dA.contributor_count?.toLocaleString(), vB: dB.contributor_count?.toLocaleString(), win: winner(dA.contributor_count, dB.contributor_count) }]
          : []),
        { label: "Language",    vA: dA.language ?? "—",               vB: dB.language ?? "—",               win: "tie" },
        { label: "Confidence",  vA: dA.confidence != null ? `${Math.round(dA.confidence * 100)}%` : "—",
                                vB: dB.confidence != null ? `${Math.round(dB.confidence * 100)}%` : "—",
                                win: winner(dA.confidence, dB.confidence) },
      ]
    : [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-white mb-6">Compare Repositories</h1>

      {/* Inputs */}
      <form onSubmit={handleCompare}>
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <RepoInput label="Repository A" owner={ownerA} repo={repoA} onOwner={setOwnerA} onRepo={setRepoA} />
          <div className="flex items-center justify-center text-gray-600 text-xl font-light select-none">vs</div>
          <RepoInput label="Repository B" owner={ownerB} repo={repoB} onOwner={setOwnerB} onRepo={setRepoB} />
        </div>
        <div className="flex justify-center">
          <button
            type="submit"
            disabled={!canSubmit || loading}
            className="px-8 py-2.5 rounded-md text-sm font-medium text-white transition disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ backgroundColor: "#238636" }}
            onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = "#2ea043"; }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "#238636"; }}
          >
            {loading ? "Comparing…" : "Compare"}
          </button>
        </div>
      </form>

      {/* Per-repo errors */}
      {errors.some(Boolean) && (
        <div className="flex gap-4 mt-4">
          {errors.map((err, i) => err && (
            <div key={i} className="flex-1 text-xs text-red-400 text-center">{err}</div>
          ))}
        </div>
      )}

      {/* Results */}
      {(dA || dB) && (
        <div className="mt-10">

          {/* Comparison table */}
          <div
            className="rounded-lg border border-gray-700 overflow-hidden mb-8"
            style={{ backgroundColor: "#161b22" }}
          >
            <table className="w-full">
              <thead>
                <tr style={{ backgroundColor: "#0d1117" }}>
                  <th className="px-4 py-3 text-left text-xs text-gray-500 uppercase tracking-wide w-32">Metric</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold" style={{ color: COLOR_A }}>
                    {dA ? <Link to={`/repo/${dA.full_name}`} className="hover:underline">{dA.full_name}</Link> : `${ownerA}/${repoA}`}
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold" style={{ color: COLOR_B }}>
                    {dB ? <Link to={`/repo/${dB.full_name}`} className="hover:underline">{dB.full_name}</Link> : `${ownerB}/${repoB}`}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {/* Genre row — special rendering */}
                <tr>
                  <td className="px-4 py-3 text-xs text-gray-500 uppercase tracking-wide">Genre</td>
                  <td className="px-4 py-3 text-center">
                    {dA?.genre ? <GenreTag genre={dA.genre} confidence={dA.confidence} /> : <span className="text-gray-600 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {dB?.genre ? <GenreTag genre={dB.genre} confidence={dB.confidence} /> : <span className="text-gray-600 text-xs">—</span>}
                  </td>
                </tr>
                {/* Tags row */}
                <tr>
                  <td className="px-4 py-3 text-xs text-gray-500 uppercase tracking-wide">Tags</td>
                  <td className="px-4 py-3 text-center"><TagList tags={dA?.tags} /></td>
                  <td className="px-4 py-3 text-center"><TagList tags={dB?.tags} /></td>
                </tr>
                {/* Numeric + string rows */}
                {rows.map(({ label, vA, vB, win }) => (
                  <tr key={label}>
                    <td className="px-4 py-3 text-xs text-gray-500 uppercase tracking-wide">{label}</td>
                    <Cell_ value={vA} win={win} side="a" />
                    <Cell_ value={vB} win={win} side="b" />
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 3 separate bar charts — one per metric for independent Y scales */}
          {dA && dB && (
            <div
              className="rounded-lg border border-gray-700 p-5"
              style={{ backgroundColor: "#161b22" }}
            >
              <h2 className="text-sm font-semibold text-white mb-1">Stats comparison</h2>
              {/* Legend */}
              <div className="flex items-center gap-4 mb-5">
                <span className="flex items-center gap-1.5 text-xs text-gray-400">
                  <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: COLOR_A }} />
                  {dA.full_name}
                </span>
                <span className="flex items-center gap-1.5 text-xs text-gray-400">
                  <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: COLOR_B }} />
                  {dB.full_name}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "Stars",       vA: dA.stars,       vB: dB.stars },
                  { label: "Forks",       vA: dA.forks,       vB: dB.forks },
                  { label: "Open Issues", vA: dA.open_issues, vB: dB.open_issues },
                ].map(({ label, vA, vB }) => (
                  <div key={label}>
                    <div className="text-xs text-gray-500 text-center mb-2">{label}</div>
                    <ResponsiveContainer width="100%" height={160}>
                      <BarChart
                        data={[
                          { name: "A", value: vA },
                          { name: "B", value: vB },
                        ]}
                        barCategoryGap="25%"
                      >
                        <XAxis
                          dataKey="name"
                          tick={{ fill: "#8b949e", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                          tickFormatter={(v) => v === "A" ? dA.full_name.split("/")[1] : dB.full_name.split("/")[1]}
                        />
                        <YAxis
                          tick={{ fill: "#8b949e", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                          width={40}
                          tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                          <Cell fill={COLOR_A} />
                          <Cell fill={COLOR_B} />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
