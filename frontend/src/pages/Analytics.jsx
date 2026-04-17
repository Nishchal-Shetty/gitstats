import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const API = import.meta.env.VITE_API_URL ?? "";

// Shared utility for formatting numbers
const fmt = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : n?.toLocaleString() ?? "—");

export default function Analytics() {
    const [data, setData] = useState({ platform: null, genres: [], trending: [], loading: true });
    const [activeGenre, setActiveGenre] = useState(null);

    useEffect(() => {
        Promise.all([
        fetch(`${API}/analytics/platform`).then(r => r.json()),
        fetch(`${API}/analytics/genres`).then(r => r.json()),
        fetch(`${API}/analytics/trending`).then(r => r.json())
        ]).then(([platform, genres, trending]) => 
        setData({ platform, genres, trending, loading: false })
        ).catch(() => setData(prev => ({ ...prev, loading: false })));
    }, []);

    if (data.loading) return <div className="p-12 text-gray-500 animate-pulse">Loading engine metrics...</div>;

    return (
        <div className="max-w-5xl mx-auto px-4 py-12 text-sm text-gray-400">
            <header className="mb-10">
                <h1 className="text-2xl font-bold text-white mb-1">Analytics</h1>
                <p>Aggregated insights across the GitStats database.</p>
            </header>

            {/* Stats Overview */}
            <div className="grid grid-cols-2 gap-4 mb-10">
                {[
                { label: "Repos", val: data.platform?.total_repos },
                { label: "Devs", val: data.platform?.total_developers },
                ].map(s => (
                    <div key={s.label} className="bg-[#161b22] border border-gray-800 p-4 rounded-lg">
                        <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">{s.label}</div>
                        <div className="text-xl font-mono text-white">{fmt(s.val)}</div>
                    </div>
                ))}
            </div>

            {/* Language & Genre Distribution*/}
            <div className="grid md:grid-cols-2 gap-8 mb-12">
                <DistributionSection 
                title="Language Distribution" 
                items={Object.entries(data.platform?.language_distribution || {}).sort((a,b) => b[1] - a[1]).slice(0, 6)} 
                />
                <DistributionSection 
                title="Genre Distribution" 
                items={Object.entries(data.platform?.genre_distribution || {}).sort((a,b) => b[1] - a[1]).slice(0, 6)} 
                isGenre 
                />
            </div>

            {/* Trending Repositories */}
            <section>
                <h2 className="text-white font-semibold mb-4">Trending Repositories</h2>
                <div className="bg-[#161b22] border border-gray-800 rounded-lg divide-y divide-gray-800">
                    {data.trending.slice(0, 10).map((repo) => (
                        <Link key={repo.full_name} to={`/repo/${repo.full_name}`} className="flex items-center p-3 hover:bg-white/[0.02] transition group">
                            <div className="flex-1 min-w-0">
                                <div className="text-white font-medium group-hover:text-indigo-400 truncate">{repo.full_name}</div>
                                <div className="text-[11px] text-gray-500 truncate">{repo.description}</div>
                            </div>
                            <div className="text-right ml-4 shrink-0">
                                <div className="flex justify-end gap-3 items-center mb-1.5">
                                    <div className="text-emerald-500 text-xs">⑂ {fmt(repo.forks)}</div>
                                    <div className="text-yellow-500 text-xs">★ {fmt(repo.stars)}</div>
                                </div> 
                                <div className="flex justify-end">
                                    <div 
                                        className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold tracking-tighter uppercase border ${
                                            repo.trend_score > 75 
                                            ? "bg-indigo-500/10 border-indigo-500/50 text-indigo-400" 
                                            : "bg-gray-800/50 border-gray-700 text-gray-500"
                                        }`}
                                        >
                                        <span>{repo.trend_score > 50 ? "▲" : "▶"}</span>
                                        <span>Score: {repo.trend_score.toFixed(0)}</span>
                                    </div>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            </section>

            {/* Genre Exploration */}
            {data.genres.length > 0 && (
            <section className="mt-12">
                <div className="mb-6">
                    <h2 className="text-white font-semibold text-lg">Genre Exploration</h2>
                    <p className="text-gray-500 text-xs mt-1">Select a genre to view top-performing repositories and language splits.</p>
                </div>

                {/* Genre Tabs */}
                <div className="flex gap-2 overflow-x-auto pb-4 no-scrollbar">
                    {data.genres.map((g) => (
                        <button
                        key={g.genre}
                        onClick={() => setActiveGenre(g.genre === activeGenre ? null : g.genre)}
                        className={`px-4 py-2 rounded-full border text-xs whitespace-nowrap transition-all ${
                            activeGenre === g.genre
                            ? "bg-indigo-500 border-indigo-400 text-white shadow-lg shadow-indigo-500/20"
                            : "bg-[#161b22] border-gray-800 text-gray-400 hover:border-gray-600"
                        }`}
                        >
                        {g.genre.replace(/_/g, ' ')}
                        </button>
                    ))}
                </div>

                {/* Active Genre Details */}
                {activeGenre && (
                <div className="grid md:grid-cols-3 gap-6 mt-4 animate-in fade-in slide-in-from-top-2 duration-300">
                    {/* Repo List */}
                    <div className="md:col-span-2 space-y-3">
                        <h3 className="text-[10px] uppercase tracking-widest text-gray-500 font-bold mb-2">Top Repositories</h3>
                        {data.genres.find(g => g.genre === activeGenre).top_repos.map(repo => (
                            <Link 
                                key={repo.full_name} 
                                to={`/repo/${repo.full_name}`}
                                className="block p-4 bg-[#161b22] border border-gray-800 rounded-lg hover:border-indigo-500/50 transition-colors"
                                >
                                <div className="flex justify-between items-start mb-1">
                                    <span className="text-white font-medium text-sm truncate mr-4">{repo.full_name}</span>
                                    
                                    <div className="flex gap-3 items-center shrink-0">
                                        <span className="text-yellow-500 text-[11px] font-mono">★ {fmt(repo.stars)}</span>
                                    </div>
                                </div>
                                <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">{repo.description}</p>
                            </Link>
                        ))}
                    </div>

                    {/* Language Breakdown */}
                    <div className="h-fit">
                        <h3 className="text-[10px] uppercase tracking-widest text-gray-500 font-bold mb-4">Top Languages</h3>
                        <div className="bg-[#0d1117] p-5 rounded-lg border border-gray-800 space-y-4">
                            {data.genres.find(g => g.genre === activeGenre).top_languages.map(lang => (
                                <div key={lang.language}>
                                    <div className="flex justify-between text-[11px] mb-1.5">
                                        <span className="text-gray-300">{lang.language}</span>
                                        <span className="text-gray-500">{lang.count} repos</span>
                                    </div>
                                    <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                                        <div 
                                            className="h-full bg-indigo-400" 
                                            style={{ width: `${(lang.count / data.genres.find(g => g.genre === activeGenre).repo_count) * 100}%` }}
                                    />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
                )}
            </section>
            )}
        </div>
    );
}

function DistributionSection({ title, items, isGenre }) {
    const max = items[0]?.[1] || 1;
    return (
        <section>
            <h3 className="text-white text-xs font-semibold mb-4 uppercase tracking-widest">{title}</h3>
            <div className="space-y-3">
                {items.map(([name, count]) => (
                    <div key={name}>
                        <div className="flex justify-between text-[11px] mb-1">
                            <span className={isGenre ? "capitalize" : ""}>{name.replace(/_/g, ' ')}</span>
                            <span className="text-gray-500">{fmt(count)}</span>
                        </div>
                        <div className="h-1.5 bg-[#21262d] rounded-full overflow-hidden">
                            <div 
                                className={`h-full ${isGenre ? 'bg-emerald-500' : 'bg-indigo-500'} opacity-80`} 
                                style={{ width: `${(count / max) * 100}%` }} 
                        />
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}