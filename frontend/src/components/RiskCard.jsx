import { AlertTriangle, Shield, CheckCircle, MinusCircle } from "lucide-react";

const riskConfig = {
  High: { icon: AlertTriangle, colorClass: "text-rose-600", bgClass: "bg-rose-50", borderClass: "border-rose-400" },
  Medium: { icon: Shield, colorClass: "text-amber-600", bgClass: "bg-amber-50", borderClass: "border-amber-400" },
  Low: { icon: CheckCircle, colorClass: "text-emerald-600", bgClass: "bg-emerald-50", borderClass: "border-emerald-400" },
  Minimal: { icon: MinusCircle, colorClass: "text-gray-500", bgClass: "bg-gray-100", borderClass: "border-gray-300" },
};

/**
 * One district row in a side list: name, a risk-coloured caption, a headline
 * figure on the right and optional supporting facts underneath.
 */
const RiskCard = ({ title, subtitle, risk, caption, value, valueLabel, facts = [], onClick }) => {
  const config = riskConfig[risk] || riskConfig.Minimal;
  const Icon = config.icon;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`glass-panel w-full text-left p-3.5 border-l-[4px] hover:bg-gray-50 transition-colors ${config.borderClass}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className={`p-2 rounded-lg shrink-0 ${config.bgClass}`}>
            <Icon className={`w-4 h-4 ${config.colorClass}`} />
          </div>
          <div className="min-w-0">
            <p className="font-bold text-gray-900 text-sm truncate">{title}</p>
            <p className="text-xs text-gray-500 truncate">{subtitle}</p>
            {caption && <p className={`text-[11px] font-bold uppercase tracking-wide mt-0.5 ${config.colorClass}`}>{caption}</p>}
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-lg font-bold text-gray-900 leading-none">{value}</p>
          <p className="text-[10px] uppercase tracking-widest text-gray-500 mt-1 font-semibold">{valueLabel}</p>
        </div>
      </div>
      {facts.length > 0 && (
        <p className="text-[11px] text-gray-500 mt-2 leading-relaxed">{facts.join(" · ")}</p>
      )}
    </button>
  );
};

export default RiskCard;
