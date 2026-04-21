import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

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

const LABEL_COLORS = {
    "good first issue": { bg: "#0d2b1a", fg: "#3fb950", border: "#238636" },
    "help wanted": { bg: "#0d2239", fg: "#388bfd", border: "#1f6feb" },
    "bug": { bg: "#2d0808", fg: "#ff7b72", border: "#da3633" },
    "enhancement": { bg: "#0d1f3c", fg: "#79c0ff", border: "#1158c7" },
    "documentation": { bg: "#1c1006", fg: "#e3b341", border: "#9e6a03" },
};
function LabelChip({ name }) {
    const style = LABEL_COLORS[name.toLowerCase()] ?? { bg: "#161b22", fg: "#8b949e", border: "#30363d" };
    return (
        <span className="text-xs rounded-full px-2 py-0.5 font-medium"
            style={{ backgroundColor: style.bg, color: style.fg, border: `1px solid ${style.border}` }}>
            {name}
        </span>
    );
}

function StatRow({ icon, label, value }) {
    if (value == null || value === 0) return null;
    return (
        <div className="flex items-center justify-between gap-4 py-1.5 border-b border-gray-800 last:border-0">
            <span className="text-xs text-gray-500">{icon} {label}</span>
            <span className="text-xs font-semibold text-white tabular-nums">
                {typeof value === "number" ? value.toLocaleString() : value}
            </span>
        </div>
    );
}

function IssueCard({ issue }) {
    return (
        <a
            href={issue.html_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex flex-col gap-2 rounded-lg p-3 h-full hover:border-indigo-500 transition-colors group/issue min-w-0"
            style={{ backgroundColor: "#0d1117", border: "1px solid #21262d" }}
        >
            <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-semibold text-white group-hover/issue:text-indigo-300 transition leading-snug flex-1 min-w-0 break-words">
                    #{issue.number} · {issue.title}
                </span>
                {issue.comments > 0 && (
                    <span className="text-xs text-gray-600 shrink-0 mt-0.5">💬 {issue.comments}</span>
                )}
            </div>
            {issue.body_excerpt && (
                <p className="text-xs text-gray-500 line-clamp-3 leading-relaxed flex-1 break-words">{issue.body_excerpt}</p>
            )}
            <div className="flex flex-wrap items-center justify-between gap-1 mt-auto pt-2">
                <div className="flex flex-wrap gap-1">
                    {issue.labels.map((l) => <LabelChip key={l} name={l} />)}
                </div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400 opacity-0 group-hover/issue:opacity-100 transition-opacity">
                    View Issue ↗
                </span>
            </div>
        </a>
    );
}

function RepoCard({ repo, username, userGenres, userTags, isExpanded, onToggle }) {
    const [owner, name] = (repo.full_name ?? "").split("/");
    const isLive = repo.source === "github";

    return (
        <div
            onClick={onToggle}
            className={`rounded-xl border cursor-pointer transition-all duration-200 hover:border-gray-500 p-4 overflow-hidden ${isExpanded ? "ring-1 ring-indigo-500/40 border-indigo-500/60" : ""}`}
            style={{ backgroundColor: "#161b22", borderColor: isExpanded ? "#58a6ff" : "#30363d" }}
        >
            <div className="flex items-start justify-between gap-2 mb-2">
                <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-xs text-gray-500 truncate">{owner}</p>
                        {isLive && (
                            <span className="text-xs rounded-full px-1.5 font-semibold shrink-0"
                                style={{ backgroundColor: "#0d2b1a", color: "#3fb950", border: "1px solid #238636" }}>
                                ● Live
                            </span>
                        )}
                    </div>
                    <p className="text-sm font-semibold text-white truncate">{name}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-yellow-400">★ {repo.stars?.toLocaleString() ?? "—"}</span>
                    <span className="text-gray-600 text-xs">{isExpanded ? "▴" : "▾"}</span>
                </div>
            </div>
            {repo.description && (
                <p className="text-xs text-gray-400 line-clamp-2 mb-3 leading-relaxed break-all">{repo.description}</p>
            )}
            <div className="flex flex-wrap items-center gap-2">
                {repo.language && (
                    <span className="text-xs text-gray-500 border border-gray-700 rounded px-2 py-0.5">{repo.language}</span>
                )}
                <GenreBadge genre={repo.genre} />
                {repo.forks != null && (
                    <span className="text-xs text-gray-600 ml-auto">⑂ {repo.forks?.toLocaleString()}</span>
                )}
            </div>
        </div>
    );
}

function ExpandedPanel({ repo, username, userGenres, userTags, onCollapse }) {
    const [owner, name] = (repo.full_name ?? "").split("/");
    const isLive = repo.source === "github";
    const [issues, setIssues] = useState(null);
    const [issueLoading, setIssueLoading] = useState(false);
    const [issueError, setIssueError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            setIssueLoading(true);
            setIssueError(null);
            try {
                const params = new URLSearchParams({
                    username: username || "",
                    genres: (userGenres ?? []).join(","),
                    tags: (userTags ?? []).join(","),
                });
                const res = await axios.get(
                    `${API}/recommendations/issues/${owner}/${name}?${params}`
                );
                if (!cancelled) setIssues(res.data.issues);
            } catch (err) {
                if (!cancelled) setIssueError(err.response?.data?.detail || "Could not load issues.");
            } finally {
                if (!cancelled) setIssueLoading(false);
            }
        };
        load();
        return () => { cancelled = true; };
    }, [owner, name, username, userGenres, userTags]);

    return (
        <div
            className="rounded-xl border transition-all duration-200 overflow-hidden"
            style={{
                backgroundColor: "#161b22",
                borderColor: "#58a6ff",
                boxShadow: "0 0 0 1px #1f6feb33",
            }}
        >
            {/* ── Top section: info left + stats right ── */}
            <div
                className="grid gap-0"
                style={{ gridTemplateColumns: "1fr 260px" }}
            >
                {/* Left: repo identity + description + pills */}
                <div className="p-5 border-r border-gray-800 min-w-0 overflow-hidden">
                    <div className="flex items-start justify-between gap-2 mb-3">
                        <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs text-gray-500">{owner} /</span>
                                <span className="text-base font-bold text-white">{name}</span>
                                {isLive && (
                                    <span className="text-xs rounded-full px-2 py-0.5 font-semibold"
                                        style={{ backgroundColor: "#0d2b1a", color: "#3fb950", border: "1px solid #238636" }}>
                                        ● Live
                                    </span>
                                )}
                            </div>
                            {repo.description && (
                                <p className="text-sm text-gray-300 leading-relaxed break-all">{repo.description}</p>
                            )}
                        </div>
                        {/* Collapse button */}
                        <button
                            onClick={onCollapse}
                            className="shrink-0 text-xs text-gray-500 hover:text-white transition px-2 py-1 rounded border border-gray-700 hover:border-gray-500"
                        >
                            ▴ Collapse
                        </button>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 mt-4">
                        {repo.language && (
                            <span className="text-xs text-gray-400 border border-gray-700 rounded px-2 py-0.5">{repo.language}</span>
                        )}
                        <GenreBadge genre={repo.genre} />
                        {(repo.topics ?? []).slice(0, 5).map((t) => (
                            <span key={t} className="text-xs rounded px-2 py-0.5"
                                style={{ backgroundColor: "#0d2239", color: "#79c0ff", border: "1px solid #1158c722" }}>
                                {t}
                            </span>
                        ))}
                    </div>

                    <div className="mt-4">
                        <a
                            href={`https://github.com/${owner}/${name}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:underline"
                        >
                            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" /></svg>
                            View on GitHub ↗
                        </a>
                    </div>
                </div>

                {/* Right: stats panel */}
                <div className="p-5">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Repo Stats</p>
                    <StatRow icon="★" label="Stars" value={repo.stars} />
                    <StatRow icon="⑂" label="Forks" value={repo.forks} />
                    <StatRow icon="👁" label="Watchers" value={repo.watchers} />
                    <StatRow icon="🐛" label="Open Issues" value={repo.open_issues} />
                    <StatRow icon="👥" label="Contributors" value={repo.contributor_count} />
                    <StatRow icon="📝" label="Commits" value={repo.commit_count} />
                    {repo.size > 0 && (
                        <StatRow icon="📦" label="Size"
                            value={repo.size > 1024 ? `${(repo.size / 1024).toFixed(1)} MB` : `${repo.size} KB`} />
                    )}
                    {repo.updated_at && (
                        <StatRow icon="🕐" label="Updated"
                            value={new Date(repo.updated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })} />
                    )}
                </div>
            </div>

            {/* ── Bottom: 3 issues in a horizontal row ── */}
            <div className="border-t border-gray-800 px-5 pb-5 pt-4">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                    Suggested issues for you
                </p>

                {issueLoading && (
                    <div className="flex items-center gap-2 py-6 justify-center text-xs text-gray-500">
                        <span className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                        Finding the best issues for your skills…
                    </div>
                )}
                {issueError && !issueLoading && (
                    <p className="text-xs text-red-400 py-2">{issueError}</p>
                )}
                {issues && !issueLoading && issues.length === 0 && (
                    <p className="text-xs text-gray-500 py-2">No open issues found for this repo.</p>
                )}
                {issues && !issueLoading && issues.length > 0 && (
                    <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${issues.length}, 1fr)` }}>
                        {issues.map((iss) => <IssueCard key={iss.number} issue={iss} />)}
                    </div>
                )}
            </div>
        </div>
    );
}

// ─── RepoGrid: manages rows + expansion ─────────────────────────────────────
const COLS = { sm: 2, lg: 3 };

function RepoGrid({ repos, username, userGenres, userTags }) {
    const [expandedName, setExpandedName] = useState(null);

    // Determine column count based on viewport (we default to lg breakpoint 3)
    const [cols, setCols] = useState(COLS.lg);
    useEffect(() => {
        const update = () => {
            const w = window.innerWidth;
            setCols(w < 640 ? 1 : w < 1024 ? COLS.sm : COLS.lg);
        };
        update();
        window.addEventListener("resize", update);
        return () => window.removeEventListener("resize", update);
    }, []);

    // Break repos into rows based on current column count
    const rows = [];
    for (let i = 0; i < repos.length; i += cols) {
        rows.push(repos.slice(i, i + cols));
    }

    return (
        <div className="flex flex-col gap-3">
            <style>{`
                @keyframes expandSlideIn {
                    from { opacity: 0; transform: translateY(-12px); }
                    to   { opacity: 1; transform: translateY(0); }
                }
            `}</style>
            {rows.map((row, rowIdx) => {
                // Is one of the cards in this row expanded?
                const expandedRepo = row.find((r) => r.full_name === expandedName);
                return (
                    <div key={rowIdx}>
                        {/* The normal grid row */}
                        <div
                            className="grid gap-3"
                            style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
                        >
                            {row.map((repo) => (
                                <RepoCard
                                    key={repo.full_name}
                                    repo={repo}
                                    username={username}
                                    userGenres={userGenres}
                                    userTags={userTags}
                                    isExpanded={repo.full_name === expandedName}
                                    onToggle={() =>
                                        setExpandedName((prev) =>
                                            prev === repo.full_name ? null : repo.full_name
                                        )
                                    }
                                />
                            ))}
                        </div>
                        {/* Expanded detail panel – rendered BELOW the entire row */}
                        {expandedRepo && (
                            <div className="mt-3" style={{ animation: "expandSlideIn 0.3s ease-out both" }}>
                                <ExpandedPanel
                                    key={expandedRepo.full_name}
                                    repo={expandedRepo}
                                    username={username}
                                    userGenres={userGenres}
                                    userTags={userTags}
                                    onCollapse={() => setExpandedName(null)}
                                />
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
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
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleRefine(); } }}
                placeholder='Try "show only Python repos", "focus on machine learning", "beginner-friendly projects"…'
                rows={3}
                className="w-full rounded-lg border border-gray-700 bg-gray-900 text-white placeholder-gray-600 px-3 py-2 text-sm resize-none focus:outline-none focus:border-indigo-500 transition mb-3"
            />

            <div className="flex items-center justify-between">
                <span className="text-xs text-gray-600">Enter to submit · Shift+Enter for new line</span>
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
    const { user: authUser } = useAuth();
    const [input, setInput] = useState("");
    const [username, setUsername] = useState(null);
    const [loading, setLoading] = useState(false);

    // Auto-fill from GitHub login AND auto-fetch recommendations
    const autoFetched = React.useRef(false);
    useEffect(() => {
        if (authUser?.username && !input && !username && !autoFetched.current) {
            setInput(authUser.username);
            autoFetched.current = true;
            // Defer so input state is set before handleSubmit reads it
            setTimeout(() => {
                handleSubmitForUser(authUser.username);
            }, 0);
        }
    }, [authUser]);
    const [error, setError] = useState(null);
    const [data, setData] = useState(null);   // { username, top_languages, user_genres, recommendations }
    const trimTo3 = (arr) => arr.slice(0, Math.floor(arr.length / 3) * 3);
    const [displayedRepos, setDisplayed] = useState([]);

    const [resumeFile, setResumeFile] = useState(null);
    const [resumeKeywords, setResumeKeywords] = useState([]);
    const [uploadingResume, setUploadingResume] = useState(false);
    const [uploadError, setUploadError] = useState(null);

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        setResumeFile(file);
        setUploadingResume(true);
        setUploadError(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await axios.post(`${API}/recommendations/upload-resume`, formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            setResumeKeywords(res.data.keywords || []);
        } catch (err) {
            setUploadError(err.response?.data?.detail || "Failed to parse resume.");
            setResumeKeywords([]);
        } finally {
            setUploadingResume(false);
            // clear the input so user can re-upload if they want
            e.target.value = null;
        }
    };

    const handleSubmitForUser = async (u) => {
        if (!u) return;
        setLoading(true);
        setError(null);
        setData(null);
        setDisplayed([]);
        setUsername(u);
        try {
            const params = new URLSearchParams();
            if (resumeKeywords.length > 0) {
                params.append("resume_keywords", resumeKeywords.join(" "));
            }
            const res = await axios.get(`${API}/recommendations/${u}?${params.toString()}`);
            setData(res.data);
            setDisplayed(trimTo3(res.data.recommendations ?? []));
        } catch (err) {
            setError(err.response?.data?.detail || "Could not load recommendations.");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e?.preventDefault();
        handleSubmitForUser(input.trim());
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

            {/* ── Search form & Upload ── */}
            <div className="flex flex-col md:flex-row gap-4 mb-4">
                <form onSubmit={handleSubmit} className="flex gap-2 flex-1">
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

                <div className="flex items-center gap-3 bg-gray-900 border border-gray-600 rounded-lg px-4 py-2 min-w-[240px]">
                    <label className={`text-sm ${uploadingResume ? 'text-gray-500' : 'text-gray-300 hover:text-indigo-400 cursor-pointer'} transition flex items-center gap-2 truncate`}>
                        📄 <span>{uploadingResume ? "Parsing resume…" : resumeFile ? resumeFile.name : "Upload Resume (PDF)"}</span>
                        <input type="file" accept="application/pdf" className="hidden" onChange={handleFileUpload} disabled={uploadingResume} />
                    </label>
                    {resumeKeywords.length > 0 && !uploadingResume && (
                        <span className="text-xs text-indigo-400 font-medium bg-indigo-900/30 px-2 py-0.5 rounded ml-auto">
                            {resumeKeywords.length} skills
                        </span>
                    )}
                </div>
            </div>

            {uploadError && <p className="text-xs text-red-400 mb-6">{uploadError}</p>}

            {resumeKeywords.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mb-10 pb-4 border-b border-gray-800">
                    <span className="text-xs text-gray-500 mr-2">Extracted Skills:</span>
                    {resumeKeywords.map((k) => (
                        <span key={k} className="text-xs rounded-full px-2 py-0.5 font-medium bg-indigo-900/30 text-indigo-400 border border-indigo-500/30">
                            {k}
                        </span>
                    ))}
                </div>
            )}

            {resumeKeywords.length === 0 && !uploadError && <div className="mb-10" />}

            {/* ── Loading ── */}
            {loading && (
                <div className="flex flex-col items-center justify-center gap-3 py-24">
                    <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-gray-400 text-sm">Analysing {username}'s profile {resumeKeywords.length ? "and resume " : ""}…</p>
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

                    {/* AI Refine box moved to top with other controls */}
                    {displayedRepos.length > 0 && (
                        <div className="mb-6">
                            <RefineBox
                                username={data.username}
                                repos={displayedRepos}
                                onRefined={(refined) => setDisplayed(trimTo3(refined))}
                            />
                        </div>
                    )}

                    {displayedRepos.length === 0 ? (
                        <div className="text-center py-16 text-gray-500 text-sm">
                            No matching repositories found in the database yet.
                            <br />
                            <span className="text-xs text-gray-600">
                                Try scraping more repos from the home page first.
                            </span>
                        </div>
                    ) : (
                        <RepoGrid
                            repos={displayedRepos}
                            username={data.username}
                            userGenres={data.user_genres}
                            userTags={data.user_tags}
                        />
                    )}
                </>
            )}
        </div>
    );
}
