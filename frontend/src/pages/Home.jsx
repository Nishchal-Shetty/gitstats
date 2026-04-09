import { useState } from "react";
import { useNavigate } from "react-router-dom";

function parseGitHubInput(value) {
  const urlMatch = value.match(/github\.com\/([^/\s]+)\/([^/\s?#]+)/);
  if (urlMatch) return { owner: urlMatch[1], repo: urlMatch[2].replace(/\/$/, "") };
  const slashMatch = value.match(/^([^/\s]+)\/([^/\s]+)$/);
  if (slashMatch) return { owner: slashMatch[1], repo: slashMatch[2] };
  return null;
}

function RepoCard() {
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [url, setUrl] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (owner.trim() && repo.trim()) {
      navigate(`/repo/${owner.trim()}/${repo.trim()}`);
    }
  };

  const handleUrlChange = (e) => {
    const val = e.target.value;
    setUrl(val);
    const parsed = parseGitHubInput(val);
    if (parsed) { setOwner(parsed.owner); setRepo(parsed.repo); }
  };

  return (
    <div
      className="flex-1 rounded-lg border border-gray-700 p-6 flex flex-col"
      style={{ backgroundColor: "#161b22" }}
    >
      <div className="mb-5">
        <h2 className="text-white font-semibold text-lg mb-1">Analyze a Repository</h2>
        <p className="text-gray-400 text-sm">Get stats, genre classification, and similar repos.</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3 flex-1">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Owner</label>
          <input
            type="text"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            placeholder="e.g. facebook"
            className="w-full rounded-md border border-gray-600 bg-gray-900 text-white placeholder-gray-500 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Repository</label>
          <input
            type="text"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="e.g. react"
            className="w-full rounded-md border border-gray-600 bg-gray-900 text-white placeholder-gray-500 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex items-center gap-2 my-1">
          <div className="flex-1 h-px bg-gray-700" />
          <span className="text-xs text-gray-500">OR</span>
          <div className="flex-1 h-px bg-gray-700" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">GitHub URL</label>
          <input
            type="text"
            value={url}
            onChange={handleUrlChange}
            placeholder="e.g. https://github.com/facebook/react"
            className="w-full rounded-md border border-gray-600 bg-gray-900 text-white placeholder-gray-500 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>
        <button
          type="submit"
          disabled={!owner.trim() || !repo.trim()}
          className="mt-auto w-full py-2 rounded-md text-sm font-medium text-white transition disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ backgroundColor: "#238636" }}
          onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = "#2ea043"; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "#238636"; }}
        >
          Analyze Repo
        </button>
      </form>
    </div>
  );
}

function parseGitHubProfileUrl(value) {
  const match = value.match(/github\.com\/([^/\s?#]+)/);
  return match ? match[1] : null;
}

function DevCard() {
  const [username, setUsername] = useState("");
  const [profileUrl, setProfileUrl] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (username.trim()) {
      navigate(`/dev/${username.trim()}`);
    }
  };

  const handleProfileUrlChange = (e) => {
    const val = e.target.value;
    setProfileUrl(val);
    const parsed = parseGitHubProfileUrl(val);
    if (parsed) setUsername(parsed);
  };

  return (
    <div
      className="flex-1 rounded-lg border border-gray-700 p-6 flex flex-col"
      style={{ backgroundColor: "#161b22" }}
    >
      <div className="mb-5">
        <h2 className="text-white font-semibold text-lg mb-1">Analyze a Developer</h2>
        <p className="text-gray-400 text-sm">Explore a GitHub user's portfolio and top languages.</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3 flex-1">
        <div>
          <label className="block text-xs text-gray-400 mb-1">GitHub Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g. torvalds"
            className="w-full rounded-md border border-gray-600 bg-gray-900 text-white placeholder-gray-500 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex items-center gap-2 my-1">
          <div className="flex-1 h-px bg-gray-700" />
          <span className="text-xs text-gray-500">OR</span>
          <div className="flex-1 h-px bg-gray-700" />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">GitHub Profile URL</label>
          <input
            type="text"
            value={profileUrl}
            onChange={handleProfileUrlChange}
            placeholder="e.g. https://github.com/torvalds"
            className="w-full rounded-md border border-gray-600 bg-gray-900 text-white placeholder-gray-500 px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>
        <button
          type="submit"
          disabled={!username.trim()}
          className="mt-auto w-full py-2 rounded-md text-sm font-medium text-white transition disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ backgroundColor: "#238636" }}
          onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.backgroundColor = "#2ea043"; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "#238636"; }}
        >
          Analyze Developer
        </button>
      </form>
    </div>
  );
}

const STEPS = [
  {
    number: "1",
    title: "Enter a repo or username",
    description: "Type in a GitHub repository (owner/repo) or a developer's GitHub username.",
  },
  {
    number: "2",
    title: "We fetch live stats",
    description: "We pull live data from GitHub and compare it against our database of 100+ classified repos.",
  },
  {
    number: "3",
    title: "Get insights",
    description: "See genre classification, similar repositories, and how the project stacks up in its category.",
  },
];

export default function Home() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">
          GitHub insights, powered by AI
        </h1>
        <p className="text-gray-400 text-lg">
          Classify repos, profile developers, and discover similar projects.
        </p>
      </div>

      {/* Cards */}
      <div className="flex flex-col sm:flex-row gap-4 mb-16">
        <RepoCard />
        <DevCard />
      </div>

      {/* How it works */}
      <div>
        <h2 className="text-white font-semibold text-base mb-6 text-center tracking-wide uppercase text-xs text-gray-500">
          How it works
        </h2>
        <div className="flex flex-col sm:flex-row gap-6">
          {STEPS.map((step) => (
            <div key={step.number} className="flex-1 flex gap-4">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 mt-0.5"
                style={{ backgroundColor: "#238636" }}
              >
                {step.number}
              </div>
              <div>
                <div className="text-white text-sm font-medium mb-1">{step.title}</div>
                <div className="text-gray-400 text-sm leading-relaxed">{step.description}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
