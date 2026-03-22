export default function StatCard({ label, value, icon, small = false }) {
  return (
    <div className={`bg-gray-900 border border-gray-800 rounded-xl ${small ? "p-3" : "p-4"}`}>
      <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
        <span>{icon}</span>
        <span>{label}</span>
      </div>
      <div className={`font-bold text-white ${small ? "text-lg" : "text-2xl"}`}>{value ?? "—"}</div>
    </div>
  );
}
