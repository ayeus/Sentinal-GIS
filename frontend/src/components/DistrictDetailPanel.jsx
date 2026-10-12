import { useState, useEffect } from "react";
import { getDistrictDetail } from "../services/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { X, MapPin, Skull, Activity, Percent, BookOpen } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import GuidancePanel from "./GuidancePanel";
import { formatDate, formatNumber } from "../config";

const DistrictDetailPanel = ({ state, district, onClose }) => {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!state || !district) return;
    let cancelled = false;
    setLoading(true);
    getDistrictDetail(state, district)
      .then(res => { if (!cancelled) setDetail(res.detail?.total_cases !== undefined ? res.detail : null); })
      .catch(err => { console.error(err); if (!cancelled) setDetail(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [state, district]);

  if (!state || !district) return null;
  const topDisease = detail?.disease_breakdown?.[0]?.Disease;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ x: 400, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 400, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed top-0 right-0 w-full sm:w-[400px] h-full bg-white shadow-2xl z-50 border-l border-gray-200 overflow-y-auto"
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
          <button onClick={onClose} aria-label="Close"
            className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors">
            <X className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        {loading ? (
          <div className="p-10 text-center text-gray-400 animate-pulse">Loading district record…</div>
        ) : !detail ? (
          <div className="p-10 text-center text-gray-500 text-sm leading-relaxed">
            No outbreak has been reported to IDSP for this district in the bulletins held by the system.
          </div>
        ) : (
          <div className="p-4 space-y-5">
            <p className="text-[11px] text-gray-500">
              All outbreaks reported between the weeks of {formatDate(detail.first_week)} and {formatDate(detail.latest_week)}.
            </p>

            {/* Key Stats */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { icon: Activity, label: "Cases", value: formatNumber(detail.total_cases), color: "text-blue-600", bg: "bg-blue-50" },
                { icon: Skull, label: "Deaths", value: formatNumber(detail.total_deaths), color: "text-red-600", bg: "bg-red-50" },
                { icon: Percent, label: "Case fatality", value: `${detail.cfr}%`, color: "text-amber-600", bg: "bg-amber-50" },
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
              <h4 className="text-sm font-bold text-gray-700 mb-2">Cases by disease</h4>
              <div className="space-y-1.5">
                {detail.disease_breakdown?.map((d) => {
                  const maxCases = detail.disease_breakdown[0]?.Cases || 1;
                  const pct = Math.min(100, (d.Cases / maxCases) * 100);
                  return (
                    <div key={d.Disease} className="flex items-center gap-2">
                      <span className="text-xs text-gray-600 w-32 truncate font-medium" title={d.Disease}>{d.Disease}</span>
                      <div className="flex-1 h-3.5 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-blue-500" style={{ width: `${pct}%` }}></div>
                      </div>
                      <span className="text-xs font-bold text-gray-800 w-12 text-right">{formatNumber(d.Cases)}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Monthly trend */}
            {detail.monthly_trend?.length > 1 && (
              <div>
                <h4 className="text-sm font-bold text-gray-700 mb-2">Cases by month of report (months with a report only)</h4>
                <ResponsiveContainer width="100%" height={120}>
                  {/* Bars, not a line: only months with a report are listed, and nothing should be drawn between them */}
                  <BarChart data={detail.monthly_trend}>
                    <XAxis dataKey="YearMonth" tick={{ fontSize: 9 }} minTickGap={24} />
                    <YAxis tick={{ fontSize: 10 }} width={30} allowDecimals={false} />
                    <Tooltip contentStyle={{ borderRadius: "8px", fontSize: "11px" }} />
                    <Bar dataKey="Cases" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Most recent outbreak records, with their IDSP identifiers */}
            {detail.recent_outbreaks?.length > 0 && (
              <div>
                <h4 className="text-sm font-bold text-gray-700 mb-2">Most recent reports</h4>
                <div className="space-y-1.5">
                  {detail.recent_outbreaks.map(o => (
                    <div key={o.outbreak_id} className="text-xs border border-gray-100 rounded-lg p-2.5 bg-gray-50/60">
                      <div className="flex justify-between gap-2">
                        <span className="font-bold text-gray-800">{o.disease}</span>
                        <span className="text-gray-500 shrink-0">week of {formatDate(o.week_start)}</span>
                      </div>
                      <div className="text-gray-600 mt-0.5">
                        {formatNumber(o.cases)} cases · {formatNumber(o.deaths)} deaths{o.status ? ` · ${o.status}` : ""}
                      </div>
                      <div className="text-[10px] text-gray-400 mt-0.5 font-mono">IDSP ID {o.outbreak_id}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Guidance for the most reported disease */}
            {topDisease && (
              <div className="pt-4 border-t border-gray-100 space-y-2">
                <h4 className="text-sm font-bold text-gray-800 flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-blue-600" /> Guidance for {topDisease}
                </h4>
                <GuidancePanel disease={topDisease} compact />
              </div>
            )}

            <p className="text-[10px] text-gray-400 text-center pt-2 border-t border-gray-100">
              {detail.data_points} outbreak records from IDSP weekly outbreak reports
            </p>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};

export default DistrictDetailPanel;
