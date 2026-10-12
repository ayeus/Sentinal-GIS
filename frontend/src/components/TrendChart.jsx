import { useState, useEffect } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Legend as RLegend
} from "recharts";
import { getTrends } from "../services/api";
import { TrendingUp } from "lucide-react";

const METRICS = [
  { key: "Outbreaks", color: "#6366f1" },
  { key: "Cases", color: "#3b82f6" },
  { key: "Deaths", color: "#ef4444" },
];

/**
 * Monthly reported outbreaks. Months for which no bulletin was ingested are
 * drawn as gaps (unknown), never as zero.
 */
const TrendChart = ({ disease, state, district }) => {
  const [data, setData] = useState([]);
  const [missingMonths, setMissingMonths] = useState(0);
  const [loading, setLoading] = useState(false);
  const [chartType, setChartType] = useState("bar");
  const [metric, setMetric] = useState("Outbreaks");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getTrends(disease, state, district)
      .then((res) => {
        if (cancelled) return;
        setData(res.trends || []);
        setMissingMonths(res.months_without_data || 0);
      })
      .catch((err) => { console.error(err); if (!cancelled) setData([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [disease, state, district]);

  if (loading) {
    return (
      <div className="glass-panel p-6 flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-400 text-sm">Loading trend…</div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="glass-panel p-6 text-center text-gray-400 text-sm h-48 flex items-center justify-center">
        No trend data available for these filters.
      </div>
    );
  }

  const color = METRICS.find(m => m.key === metric).color;
  const toggle = (options, value, onChange) => (
    <div className="flex gap-1 bg-gray-100 rounded-md p-0.5">
      {options.map((option) => (
        <button key={option} onClick={() => onChange(option)}
          className={`px-3 py-1 rounded text-xs font-bold capitalize ${value === option ? "bg-white text-blue-700 shadow-sm" : "text-gray-500"}`}>
          {option}
        </button>
      ))}
    </div>
  );
  const tooltip = (
    <Tooltip
      contentStyle={{ borderRadius: "8px", fontSize: "12px", border: "1px solid #e5e7eb" }}
      formatter={(value, name) => [value ?? "no bulletin", name]}
      labelFormatter={(label, payload) => {
        const bulletins = payload?.[0]?.payload?.Bulletins;
        return `${label} · ${bulletins ? `${bulletins} bulletin${bulletins === 1 ? "" : "s"} ingested` : "no bulletin ingested"}`;
      }}
    />
  );

  return (
    <div className="glass-panel p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="text-base font-bold text-gray-800 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-blue-600" />
          Monthly trend: {disease || "all diseases"}
          {district && <span className="text-gray-400 text-sm font-normal ml-1">({district})</span>}
        </h3>
        <div className="flex gap-2">
          {toggle(METRICS.map(m => m.key), metric, setMetric)}
          {toggle(["bar", "area"], chartType, setChartType)}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        {chartType === "area" ? (
          <AreaChart data={data}>
            <defs>
              <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="YearMonth" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} minTickGap={18} />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
            {tooltip}
            <Area type="monotone" dataKey={metric} stroke={color} fill="url(#trendGrad)" strokeWidth={2} connectNulls={false} />
          </AreaChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="YearMonth" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} minTickGap={18} />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
            {tooltip}
            <RLegend wrapperStyle={{ fontSize: "12px" }} />
            <Bar dataKey={metric} fill={color} radius={[3, 3, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
      {missingMonths > 0 && (
        <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mt-3 leading-relaxed">
          {missingMonths} of {data.length} months have no bulletin in the system and appear as gaps. They are missing
          data, not months without outbreaks. Months with only some of their weekly bulletins are under-counted
          (hover a month to see how many were ingested).
        </p>
      )}
    </div>
  );
};

export default TrendChart;
