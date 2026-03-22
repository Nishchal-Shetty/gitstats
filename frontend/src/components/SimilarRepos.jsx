import { Link } from "react-router-dom";
import GenreTag from "./GenreTag";

function RepoCard({ repo }) {
  const [owner, name] = repo.full_name.split("/");

  return (
    <Link
      to={`/repo/${owner}/${name}`}
      className="block rounded-lg border border-gray-700 p-4 hover:border-gray-500 transition"
      style={{ backgroundColor: "#161b22" }}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-sm font-medium text-white truncate">{repo.full_name}</span>
        <span className="text-xs text-yellow-400 shrink-0">★ {repo.stars?.toLocaleString()}</span>
      </div>

      {repo.description && (
        <p className="text-xs text-gray-400 line-clamp-2 mb-3">{repo.description}</p>
      )}

      <div className="flex items-center justify-between gap-2 flex-wrap">
        {repo.language && (
          <span className="text-xs text-gray-500 border border-gray-700 rounded px-2 py-0.5">
            {repo.language}
          </span>
        )}
        {repo.genre && <GenreTag genre={repo.genre} confidence={repo.confidence} />}
      </div>
    </Link>
  );
}

export default function SimilarRepos({ repos }) {
  if (!repos?.length) return null;

  return (
    <div>
      <h2 className="text-sm font-semibold text-white mb-4">Similar Repositories</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {repos.map((repo) => (
          <RepoCard key={repo.full_name} repo={repo} />
        ))}
      </div>
    </div>
  );
}
