const Legend = () => {
  const levels = [
    { label: "High Risk", colors: ["#fb7185", "#f43f5e", "#e11d48", "#be123c"] },
    { label: "Medium Risk", colors: ["#fbbf24", "#f59e0b", "#d97706", "#b45309"] },
    { label: "Low Risk", colors: ["#34d399", "#10b981", "#059669", "#047857"] },
  ];
  
  return (
    <div className="glass-panel p-5 mt-4">
      <h3 className="text-xs font-bold uppercase tracking-widest mb-4 flex justify-between items-center text-gray-700">
        <span className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
          Risk Intensity Legend
        </span>
        <span className="text-[10px] text-gray-500 font-bold normal-case flex items-center gap-1">
          Lighter <span className="text-gray-400">&rarr;</span> Darker (Confidence)
        </span>
      </h3>
      <div className="flex flex-col gap-3">
        {levels.map((level) => (
          <div key={level.label} className="flex items-center gap-4">
            <span className="text-xs font-bold w-24 text-gray-600 tracking-wider">{level.label}</span>
            <div className="flex flex-1 h-3 rounded-full overflow-hidden border border-gray-200">
              {level.colors.map((c, i) => (
                <div key={i} className="flex-1" style={{ backgroundColor: c }} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Legend;