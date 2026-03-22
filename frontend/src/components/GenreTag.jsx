const GENRE_STYLES = {
  web_frontend:    { bg: "#1c2d3d", text: "#79c0ff" },
  web_backend:     { bg: "#1c2d1c", text: "#56d364" },
  mobile:          { bg: "#2d1c3d", text: "#d2a8ff" },
  devtools:        { bg: "#2d2d1c", text: "#e3b341" },
  data_science:    { bg: "#3d1c2d", text: "#ff7b72" },
  infrastructure:  { bg: "#1c3d3d", text: "#39d3c3" },
  security:        { bg: "#3d1c1c", text: "#ffa657" },
  game_dev:        { bg: "#1c1c3d", text: "#79c0ff" },
  systems:         { bg: "#2d1c1c", text: "#ffa657" },
  open_source_lib: { bg: "#1e2d1e", text: "#56d364" },
};

const FALLBACK = { bg: "#21262d", text: "#8b949e" };

export default function GenreTag({ genre, confidence }) {
  if (!genre || genre === "unknown") return null;
  const { bg, text } = GENRE_STYLES[genre] ?? FALLBACK;
  const label = genre.replace(/_/g, " ");
  const pct = confidence != null ? Math.round(confidence * 100) : null;

  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full"
      style={{ backgroundColor: bg, color: text }}
    >
      {label}
      {pct != null && (
        <span
          className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
          style={{ backgroundColor: "rgba(0,0,0,0.25)", color: text }}
        >
          {pct}%
        </span>
      )}
    </span>
  );
}
