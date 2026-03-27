import { useState, useEffect } from "react";
import TrendChart from "../components/TrendChart";
import AnomalyPanel from "../components/AnomalyPanel";
import CoOccurrenceHeatmap from "../components/CoOccurrenceHeatmap";
import { getDiseases, getAvailableYears } from "../services/api";

const AnalyticsPage = () => {
  const [disease, setDisease] = useState("Dengue");
  const [year, setYear] = useState(null);
  const [diseasesList, setDiseasesList] = useState([]);
  const [yearsList, setYearsList] = useState([]);

  useEffect(() => {
    getDiseases().then(res => setDiseasesList(res.diseases || [])).catch(console.error);
    getAvailableYears().then(res => {
      const years = res.years || [];
      setYearsList(years);
      if (years.length > 0) setYear(years[years.length - 1]);
    }).catch(console.error);
  }, []);

  return (
    <div className="container mx-auto px-6 py-8 space-y-8">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-4">
        <h2 className="text-xl font-bold text-gray-900 flex-1">🔬 Advanced Analytics</h2>
        {diseasesList.length > 0 && (
          <select value={disease} onChange={e => setDisease(e.target.value)}
            className="bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-sm font-medium focus:ring-2 focus:ring-blue-500/50 focus:outline-none">
            <option value="">All Diseases</option>
            {diseasesList.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        )}
        <select value={year || ""} onChange={e => setYear(Number(e.target.value))}
          className="bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-sm font-medium focus:ring-2 focus:ring-blue-500/50 focus:outline-none">
          {yearsList.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      {/* Trend + Anomaly side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrendChart disease={disease || null} />
        <AnomalyPanel disease={disease || null} year={year} />
      </div>

      {/* Co-occurrence full width */}
      <CoOccurrenceHeatmap year={year} />
    </div>
  );
};

export default AnalyticsPage;
