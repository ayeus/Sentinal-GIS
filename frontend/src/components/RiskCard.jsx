import { motion } from "framer-motion";
import { Shield, AlertTriangle, CheckCircle, Radio } from "lucide-react";

const riskConfig = {
  High: { icon: AlertTriangle, colorClass: "text-red-600", bgClass: "bg-red-50", borderClass: "border-red-400" },
  Medium: { icon: Shield, colorClass: "text-amber-600", bgClass: "bg-amber-50", borderClass: "border-amber-400" },
  Low: { icon: CheckCircle, colorClass: "text-emerald-600", bgClass: "bg-emerald-50", borderClass: "border-emerald-400" },
};

const RiskCard = ({ state, risk, confidence, index, hasLiveSignal }) => {
  const config = riskConfig[risk] || riskConfig["Low"];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: index * 0.03 }}
      className={`glass-panel p-4 border-l-[4px] hover:bg-gray-50 transition-all cursor-pointer group relative overflow-hidden ${config.borderClass}`}
    >
      {hasLiveSignal && (
        <div className="absolute top-0 right-0 px-2 py-0.5 bg-red-500 text-white text-[9px] font-bold rounded-bl-lg flex items-center gap-1">
          <Radio className="w-3 h-3 animate-pulse" /> NEWS VERIFIED
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`p-2.5 rounded-lg ${config.bgClass} group-hover:scale-105 transition-transform`}>
            <Icon className={`w-5 h-5 ${config.colorClass}`} />
          </div>
          <div>
            <p className="font-bold text-gray-900 text-sm tracking-wide">{state}</p>
            <p className={`text-xs font-bold uppercase tracking-wider mt-0.5 ${config.colorClass}`}>
              {risk} Risk
            </p>
          </div>
        </div>
        {!hasLiveSignal && (
          <div className="text-right">
            <p className="text-lg font-bold text-gray-900">
              {(confidence * 100).toFixed(1)}<span className="text-sm text-gray-500 font-medium">%</span>
            </p>
            <p className="text-[10px] uppercase tracking-widest text-gray-500 mt-0.5 font-semibold">confidence</p>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default RiskCard;