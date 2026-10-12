import { RISK_COLORS, NO_DATA_COLOR } from "../config";

/**
 * Map legend. `items` is [{ risk, label, hint }]; colors come from the shared
 * palette so the legend can never drift from the map.
 */
const Legend = ({ title, items, emptyLabel = "Nothing reported", note }) => (
  <div className="glass-panel p-4">
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
      <span className="text-xs font-bold uppercase tracking-widest text-gray-700">{title}</span>
      {items.map(({ risk, label, hint }) => (
        <span key={risk} className="flex items-center gap-2 text-xs text-gray-700">
          <span className="w-3.5 h-3.5 rounded-sm" style={{ backgroundColor: RISK_COLORS[risk] }} />
          <span className="font-bold">{label}</span>
          {hint && <span className="text-gray-500">{hint}</span>}
        </span>
      ))}
      <span className="flex items-center gap-2 text-xs text-gray-500">
        <span className="w-3.5 h-3.5 rounded-sm border border-gray-300" style={{ backgroundColor: NO_DATA_COLOR }} />
        {emptyLabel}
      </span>
    </div>
    {note && <p className="text-[11px] text-gray-500 mt-2 leading-relaxed">{note}</p>}
  </div>
);

export default Legend;
