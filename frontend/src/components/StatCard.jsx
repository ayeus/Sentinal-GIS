/** Headline figure with a label and an optional explanatory line. */
const StatCard = ({ label, value, hint, tone = "text-gray-900", border = "border-gray-300" }) => (
  <div className={`glass-panel p-5 border-l-[4px] ${border}`}>
    <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">{label}</p>
    <span className={`text-3xl font-bold ${tone}`}>{value}</span>
    {hint && <p className="text-[11px] text-gray-500 mt-1.5 leading-snug">{hint}</p>}
  </div>
);

export default StatCard;
