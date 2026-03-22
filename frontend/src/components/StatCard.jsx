export default function StatCard({ title, value, average, icon }) {
  const getColor = () => {
    if (average == null || value == null) return "#e6edf3";
    if (value >= average) return "#56d364";                          // green: at or above
    if (value >= average * 0.8) return "#e3b341";                   // yellow: within 20% below
    return "#ff7b72";                                                // red: far below
  };

  return (
    <div
      className="flex-1 rounded-lg border border-gray-700 p-4"
      style={{ backgroundColor: "#161b22" }}
    >
      <div className="flex items-center gap-1.5 text-xs text-gray-500 uppercase tracking-wide mb-2">
        {icon && <span>{icon}</span>}
        <span>{title}</span>
      </div>
      <div className="text-2xl font-bold" style={{ color: getColor() }}>
        {value?.toLocaleString() ?? "—"}
      </div>
      {average != null && (
        <div className="text-xs text-gray-500 mt-1">
          avg {Math.round(average).toLocaleString()}
        </div>
      )}
    </div>
  );
}
