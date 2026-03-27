import { useState, useEffect } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Legend as RLegend
} from "recharts";
import { getTrends } from "../services/api";
import { TrendingUp } from "lucide-react";

const TrendChart = ({ disease, state, district }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [chartType, setChartType] = useState("area");

  useEffect(() => {
    if (!disease) return;
    setLoading(true);
    getTrends(disease, state, district)
      .then((res) => setData(res.trends || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [disease, state, district]);

  if (loading) {
    return (
      <div className="glass-panel p-6 flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-400 text-sm">Loading Seasonal Trends…</div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className="glass-panel p-6 text-center text-gray-400 text-sm h-48 flex items-center justify-center">
        No trend data available. Select a disease to view seasonal patterns.
      </div>
    );
  }

  return (
    <div className="glass-panel p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-gray-800 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-blue-600" />
          Seasonal Trend — {disease || "All Diseases"}
          {district && <span className="text-gray-400 text-sm font-normal ml-1">({district})</span>}
        </h3>
        <div className="flex gap-1 bg-gray-100 rounded-md p-0.5">
          {["area", "bar"].map((t) => (
            <button
              key={t}
              onClick={() => setChartType(t)}
              className={`px-3 py-1 rounded text-xs font-bold capitalize ${
                chartType === t ? "bg-white text-blue-700 shadow-sm" : "text-gray-500"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        {chartType === "area" ? (
          <AreaChart data={data}>
            <defs>
              <linearGradient id="casesGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="deathsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="YearMonth" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ borderRadius: "8px", fontSize: "12px", border: "1px solid #e5e7eb" }} />
            <Area type="monotone" dataKey="Cases" stroke="#3b82f6" fill="url(#casesGrad)" strokeWidth={2} />
            <Area type="monotone" dataKey="Deaths" stroke="#ef4444" fill="url(#deathsGrad)" strokeWidth={1.5} />
          </AreaChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="YearMonth" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ borderRadius: "8px", fontSize: "12px" }} />
            <RLegend wrapperStyle={{ fontSize: "12px" }} />
            <Bar dataKey="Cases" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Deaths" fill="#ef4444" radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
};

export default TrendChart;