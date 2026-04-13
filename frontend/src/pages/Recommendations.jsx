import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─── Helpers ────────────────────────────────────────────────────────────────

const GENRE_COLORS = {
    web_frontend: "#388bfd",
    web_backend: "#56d364",
    mobile: "#d2a8ff",
    devtools: "#ffa657",
    data_science: "#79c0ff",
    infrastructure: "#e3b341",
    security: "#ff7b72",
    game_dev: "#39d3c3",
    systems: "#f778ba",
    open_source_lib: "#8b949e",
};

function GenreBadge({ genre }) {
    if (!genre || genre === "unknown") return null;
    const color = GENRE_COLORS[genre] ?? "#8b949e";
    const label = genre.replace(/_/g, " ");
    return (
        <span
            className="text-xs rounded-full px-2 py-0.5 font-medium"
            style={{ backgroundColor: `${color}22`, color, border: `1px solid ${color}44` }}
        >
            {label}
        </span>
    );
}

function RepoCard({ repo }) {
    const [owner, name] = (repo.full_name ?? "").split("/");
    const isLive = repo.source === "github";
    return (
        <Link
            to={`/repo/${owner}/${name}`}
            className="block rounded-xl border border-gray-700 p-4 hover:border-indigo-500 transition-all duration-150 group"
            style={{ backgroundColor: "#161b22" }}
        >
            {/* Header row */}
            <div className="flex items-start justify-between gap-2 mb-2">
                <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-xs text-gray-500 truncate">{owner}</p>
                        {isLive && (
                            <span
                                className="text-xs rounded-full px-1.5 py-0 font-semibold shrink-0"
                                style={{ backgroundColor: "#0d2b1a", color: "#3fb950", border: "1px solid #2ea04326" }}
                            >
                                ● Live
                            </span>
                        )}
                    </div>
                    <p className="text-sm font-semibold text-white truncate group-hover:text-indigo-300 transition">
                        {name}
                    </p>
                </div>
                <span className="text-xs text-yellow-400 shrink-0 mt-1">
                    ★ {repo.stars?.toLocaleString() ?? "—"}
                </span>
            </div>

            {/* Description */}
            {repo.description && (
                <p className="text-xs text-gray-400 line-clamp-2 mb-3 leading-relaxed">
                    {repo.description}
                </p>
            )}

            {/* Footer pills */}
            <div className="flex flex-wrap items-center gap-2">
                {repo.language && (
                    <span className="text-xs text-gray-500 border border-gray-700 rounded px-2 py-0.5">
                        {repo.language}
                    </span>
                )}
                <GenreBadge genre={repo.genre} />
                {repo.forks != null && (
                    <span className="text-xs text-gray-600 ml-auto">⑂ {repo.forks.toLocaleString()}</span>
                )}
            </div>
        </Link>
    );
}

// ─── Refine box ─────────────────────────────────────────────────────────────

function RefineBox({ username, repos, onRefined }) {
    const [prompt, setPrompt] = useState("");
    const [refining, setRefining] = useState(false);
    const [error, setError] = useState(null);

    const handleRefine = async () => {
        if (!prompt.trim() || refining) return;
        setRefining(true);
        setError(null);
        try {
            const res = await axios.post(`${API}/recommendations/refine`, {
                username,
                prompt: prompt.trim(),
                repos,
            });
            onRefined(res.data.repos);
            if (res.data.warning) {
                setError("⚠️ AI refinement unavailable — showing original list. (" + res.data.warning.split(".")[0] + ")");
            }
        } catch (err) {
            setError(err.response?.data?.detail || "Refinement failed. Please try again.");
        } finally {
            setRefining(false);
        }
    };

    return (
        <div
            className="rounded-xl border border-indigo-800 p-5 mt-10"
            style={{ backgroundColor: "#0d1117", borderColor: "#30363d" }}
        >
            {/* Glowing header */}
            <div className="flex items-center gap-2 mb-3">
                <span className="text-indigo-400 text-lg">✦</span>
                <h3 className="text-sm font-semibold text-white">Refine with AI</h3>
                <span className="text-xs text-gray-500">— ask Claude to filter or re-rank results</span>
            </div>

            <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleRefine(); }}
                placeholder='Try "show only Python repos", "focus on machine learning", "beginner-friendly projects"…'
                rows={3}
                className="w-full rounded-lg border border-gray-700 bg-gray-900 text-white placeholder-gray-600 px-3 py-2 text-sm resize-none focus:outline-none focus:border-indigo-500 transition mb-3"
            />

            <div className="flex items-center justify-between">
                <span className="text-xs text-gray-600">⌘ Enter to submit</span>
                <button
                    onClick={handleRefine}
                    disabled={!prompt.trim() || refining}
                    className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium text-white transition disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{ backgroundColor: "#7c3aed" }}
                    onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = "#6d28d9"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "#7c3aed"; }}
                >
                    {refining ? (
                        <>
                            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            Refining…
                        </>
                    ) : (
                        "Refine results"
                    )}
                </button>
            </div>

            {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
        </div>
    );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function Recommendations() {
    const [input, setInput] = useState("");
    const [username, setUsername] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [data, setData] = useState(null);   // { username, top_languages, user_genres, recommendations }
    const [displayedRepos, setDisplayed] = useState([]);

    const handleSubmit = async (e) => {
        e?.preventDefault();
        const u = input.trim();
        if (!u) return;
        setLoading(true);
        setError(null);
        setData(null);
        setDisplayed([]);
        setUsername(u);
        try {
            const res = await axios.get(`${API}/recommendations/${u}`);
            setData(res.data);
            setDisplayed(res.data.recommendations ?? []);
        } catch (err) {
            setError(err.response?.data?.detail || "Could not load recommendations.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-5xl mx-auto px-4 py-10">

            {/* ── Page title ── */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white tracking-tight mb-2">
                    Repo <span className="text-indigo-400">Recommendations</span>
                </h1>
                <p className="text-gray-400 text-sm leading-relaxed">
                    Enter a GitHub username to get AI-powered suggestions for public repos that
                    match your skills and interests. Then refine the list with a prompt.
                </p>
            </div>

            {/* ── Search form ── */}
            <form onSubmit={handleSubmit} className="flex gap-2 mb-10">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="GitHub username (e.g. torvalds)"
                    className="flex-1 rounded-lg border border-gray-600 bg-gray-900 text-white placeholder-gray-500 px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition"
                />
                <button
                    type="submit"
                    disabled={!input.trim() || loading}
                    className="px-5 py-2.5 rounded-lg text-sm font-medium text-white transition disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{ backgroundColor: "#238636" }}
                    onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = "#2ea043"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "#238636"; }}
                >
                    {loading ? "Loading…" : "Get Recommendations"}
                </button>
            </form>

            {/* ── Loading ── */}
            {loading && (
                <div className="flex flex-col items-center justify-center gap-3 py-24">
                    <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-gray-400 text-sm">Analysing {username}'s profile…</p>
                </div>
            )}

            {/* ── Error ── */}
            {error && !loading && (
                <div
                    className="rounded-lg border border-red-800 px-5 py-4 text-sm"
                    style={{ backgroundColor: "#1a0000" }}
                >
                    <p className="text-red-400 font-medium mb-1">Failed to load recommendations</p>
                    <p className="text-red-300 text-xs">{error}</p>
                </div>
            )}

            {/* ── Results ── */}
            {data && !loading && (
                <>
                    {/* Context pills */}
                    <div className="flex flex-wrap items-center gap-3 mb-6">
                        <span className="text-sm text-gray-400">
                            Recommendations for{" "}
                            <Link to={`/dev/${data.username}`} className="text-indigo-400 hover:underline font-medium">
                                @{data.username}
                            </Link>
                        </span>

                        {data.top_languages?.length > 0 && (
                            <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="text-xs text-gray-600">top langs:</span>
                                {data.top_languages.map((l) => (
                                    <span key={l} className="text-xs border border-gray-700 rounded px-2 py-0.5 text-gray-400">
                                        {l}
                                    </span>
                                ))}
                            </div>
                        )}

                        {data.user_genres?.length > 0 && (
                            <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="text-xs text-gray-600">genres:</span>
                                {data.user_genres.map((g) => (
                                    <GenreBadge key={g} genre={g} />
                                ))}
                            </div>
                        )}

                        {data.user_tags?.length > 0 && (
                            <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="text-xs text-gray-600">tags:</span>
                                {data.user_tags.slice(0, 6).map((t) => (
                                    <span
                                        key={t}
                                        className="text-xs rounded px-2 py-0.5"
                                        style={{ backgroundColor: "#21262d", color: "#8b949e", border: "1px solid #30363d" }}
                                    >
                                        {t}
                                    </span>
                                ))}
                            </div>
                        )}

                        <span className="ml-auto text-xs text-gray-600">
                            {displayedRepos.length} repo{displayedRepos.length !== 1 ? "s" : ""}
                        </span>
                    </div>

                    {displayedRepos.length === 0 ? (
                        <div className="text-center py-16 text-gray-500 text-sm">
                            No matching repositories found in the database yet.
                            <br />
                            <span className="text-xs text-gray-600">
                                Try scraping more repos from the home page first.
                            </span>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {displayedRepos.map((repo) => (
                                <RepoCard key={repo.full_name} repo={repo} />
                            ))}
                        </div>
                    )}

                    {/* AI Refine box — always shown once we have results */}
                    <RefineBox
                        username={data.username}
                        repos={displayedRepos}
                        onRefined={(refined) => setDisplayed(refined)}
                    />
                </>
            )}
        </div>
    );
}
