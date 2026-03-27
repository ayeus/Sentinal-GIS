import { useState, useEffect, useCallback } from "react";
import { getDistrictDetail, getHealthAdvisor } from "../services/api";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer
} from "recharts";
import { X, MapPin, Skull, Activity, Percent, BrainCircuit, ShieldAlert, Sparkles, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const DistrictDetailPanel = ({ state, district, onClose }) => {
  const [detail, setDetail] = useState(null);
  const [advisor, setAdvisor] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDetail = useCallback(async () => {
    if (!state || !district) return;
    setLoading(true);
    try {
      const res = await getDistrictDetail(state, district);
      setDetail(res.detail || null);
      
      // Fetch AI Advisor for the top disease
      if (res.detail?.disease_breakdown?.length > 0) {
        const topDisease = res.detail.disease_breakdown[0].Disease;
        const advRes = await getHealthAdvisor(topDisease, district);
        setAdvisor(advRes);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [state, district]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  if (!state || !district) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: 400, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 400, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed top-0 right-0 w-[380px] h-full bg-white shadow-2xl z-50 border-l border-gray-200 overflow-y-auto"
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 p-4 flex items-center justify-between z-10">
          <div>
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-blue-600" />
              {district}
            </h3>
            <p className="text-xs text-gray-500">{state}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        {loading ? (
          <div className="p-10 text-center text-gray-400 animate-pulse">Loading district intel…</div>
        ) : !detail ? (
          <div className="p-10 text-center text-gray-400">No data found for this district.</div>
        ) : (
          <div className="p-4 space-y-5">
            {/* Key Stats */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { icon: Activity, label: "Cases", value: detail.total_cases, color: "text-blue-600", bg: "bg-blue-50" },
                { icon: Skull, label: "Deaths", value: detail.total_deaths, color: "text-red-600", bg: "bg-red-50" },
                { icon: Percent, label: "CFR", value: `${detail.cfr}%`, color: "text-amber-600", bg: "bg-amber-50" },
              ].map((s) => (
                <div key={s.label} className={`rounded-xl p-3 text-center ${s.bg} border border-gray-100`}>
                  <s.icon className={`w-5 h-5 mx-auto mb-1 ${s.color}`} />
                  <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
                  <div className="text-[10px] text-gray-500 font-medium uppercase">{s.label}</div>
                </div>
              ))}
            </div>

            {/* Disease Breakdown */}
            <div>
              <h4 className="text-sm font-bold text-gray-700 mb-2">Disease Breakdown</h4>
              <div className="space-y-1.5">
                {detail.disease_breakdown?.map((d) => {
                  const maxCases = detail.disease_breakdown[0]?.Cases || 1;
                  const pct = Math.min(100, (d.Cases / maxCases) * 100);
                  return (
                    <div key={d.Disease} className="flex items-center gap-2">
                      <span className="text-xs text-gray-600 w-24 truncate font-medium">{d.Disease}</span>
                      <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-blue-400 to-blue-600"
                          style={{ width: `${pct}%` }}
                        ></div>
                      </div>
                      <span className="text-xs font-bold text-gray-800 w-12 text-right">{d.Cases}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Sparkline Trend */}
            {detail.monthly_trend?.length > 0 && (
              <div>
                <h4 className="text-sm font-bold text-gray-700 mb-2">Monthly Trend</h4>
                <ResponsiveContainer width="100%" height={120}>
                  <AreaChart data={detail.monthly_trend}>
                    <defs>
                      <linearGradient id="detailGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="YearMonth" tick={false} />
                    <YAxis tick={{ fontSize: 10 }} width={30} />
                    <Tooltip contentStyle={{ borderRadius: "8px", fontSize: "11px" }} />
                    <Area type="monotone" dataKey="Cases" stroke="#6366f1" fill="url(#detailGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* AI Advisor Section — Phase 4 */}
            {advisor && (
              <div className="pt-4 border-t border-gray-100 space-y-4">
                <div className="flex items-center gap-2 mb-1">
                  <div className="p-1.5 bg-purple-50 rounded-lg">
                    <BrainCircuit className="w-4 h-4 text-purple-600" />
                  </div>
                  <h4 className="text-sm font-bold text-gray-800">AI Health Advisor</h4>
                </div>
                
                <div className="space-y-3">
                  <div className="bg-amber-50/50 border border-amber-100 rounded-xl p-3">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-amber-700 uppercase mb-1">
                      <AlertCircle className="w-3 h-3" /> Probable Cause
                    </div>
                    <p className="text-xs text-gray-700 leading-relaxed font-medium">
                      {advisor.causes}
                    </p>
                  </div>

                  <div className="bg-emerald-50/50 border border-emerald-100 rounded-xl p-3">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-700 uppercase mb-1">
                      <ShieldAlert className="w-3 h-3" /> Prevention & Safety
                    </div>
                    <p className="text-xs text-gray-700 leading-relaxed font-medium">
                      {advisor.prevention}
                    </p>
                  </div>

                  <div className="bg-blue-50 border border-blue-100 rounded-xl p-3">
                    <div className="flex items-center gap-2 text-[10px] font-bold text-blue-700 uppercase mb-1">
                      <Sparkles className="w-3 h-3" /> Clinical Suggestion
                    </div>
                    <p className="text-xs text-gray-700 leading-relaxed font-medium">
                      {advisor.suggestion}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <p className="text-[10px] text-gray-400 text-center pt-2 border-t border-gray-100">
              Based on {detail.data_points} historical data points • {advisor?.timestamp}
            </p>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default DistrictDetailPanel;
