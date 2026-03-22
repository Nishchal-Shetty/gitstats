const GENRE_COLORS = {
  "Web Frontend": "bg-blue-900 text-blue-300",
  "Web Backend": "bg-green-900 text-green-300",
  "Full Stack": "bg-teal-900 text-teal-300",
  "Mobile": "bg-purple-900 text-purple-300",
  "CLI Tool": "bg-yellow-900 text-yellow-300",
  "Library / SDK": "bg-orange-900 text-orange-300",
  "DevOps / Infrastructure": "bg-red-900 text-red-300",
  "Data Science / ML": "bg-pink-900 text-pink-300",
  "Game Development": "bg-indigo-900 text-indigo-300",
  "Security / Cryptography": "bg-rose-900 text-rose-300",
  "Embedded / IoT": "bg-cyan-900 text-cyan-300",
  "Desktop App": "bg-violet-900 text-violet-300",
  "API / Integration": "bg-lime-900 text-lime-300",
  "Documentation": "bg-gray-800 text-gray-300",
  "Other": "bg-gray-800 text-gray-400",
};

export default function GenreTag({ genre, small = false }) {
  const color = GENRE_COLORS[genre] || GENRE_COLORS["Other"];
  return (
    <span className={`${color} ${small ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1"} rounded-full font-medium whitespace-nowrap`}>
      {genre}
    </span>
  );
}
