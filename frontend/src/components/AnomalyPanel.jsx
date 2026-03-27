import { useState, useEffect } from "react";
import { getAnomalies } from "../services/api";
import { AlertTriangle, ShieldAlert, Siren } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const SEVERITY_STYLES = {
  Critical: { bg: "bg-red-50", border: "border-red-400", text: "text-red-700", icon: Siren },
  Severe: { bg: "bg-amber-50", border: "border-amber-400", text: "text-amber-700", icon: ShieldAlert },
  Warning: { bg: "bg-yellow-50", border: "border-yellow-500", text: "text-yellow-700", icon: AlertTriangle },
};

const AnomalyPanel = ({ disease, year }) => {
  const [anomalies, setAnomalies] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getAnomalies(disease, year)
      .then((res) => {
        setAnomalies(res.anomalies || []);
        setStats({ mean: res.mean_cases, std: res.std_cases, total: res.total_flagged });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [disease, year]);

  if (loading) {
    return <div className="glass-panel p-6 text-center text-gray-400 text-sm animate-pulse">Analyzing anomalies…</div>;
  }

  if (!anomalies.length) {
    return (
      <div className="glass-panel p-5 text-center text-sm text-emerald-600 font-medium border border-emerald-200 bg-emerald-50/50">
        ✅ No anomalous outbreaks detected — all districts within normal range.
      </div>
    );
  }

  return (
    <div className="glass-panel p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-bold text-gray-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          Early Warning — {stats.total || 0} Anomalies
        </h3>
        <span className="text-xs text-gray-400">μ={stats.mean} σ={stats.std}</span>
      </div>
      <div className="space-y-2 max-h-[300px] overflow-y-auto custom-scrollbar pr-1">
        <AnimatePresence>
          {anomalies.map((a, i) => {
            const sev = SEVERITY_STYLES[a.severity] || SEVERITY_STYLES.Warning;
            const Icon = sev.icon;
            return (
              <motion.div
                key={a.District + a.State}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`p-3 rounded-lg border-l-[3px] ${sev.border} ${sev.bg}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-bold text-gray-800">{a.District}, {a.State}</p>
                    <p className={`text-xs font-bold mt-0.5 ${sev.text}`}>
                      <Icon className="w-3 h-3 inline mr-1" />
                      {a.severity} · Z-score: {a.z_score}
                    </p>
                  </div>
                  <span className="text-sm font-bold text-gray-700 bg-white px-2 py-0.5 rounded-md shadow-sm">
                    {a.Cases} cases
                  </span>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default AnomalyPanel;
