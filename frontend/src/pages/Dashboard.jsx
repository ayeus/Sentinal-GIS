import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Globe, Loader2, BarChart3, Satellite, Map as MapIcon, Wind } from "lucide-react";

import MapView from "../components/MapView";
import RiskCard from "../components/RiskCard";
import Legend from "../components/Legend";
import TrendChart from "../components/TrendChart";
import AnomalyPanel from "../components/AnomalyPanel";
import CoOccurrenceHeatmap from "../components/CoOccurrenceHeatmap";
import DistrictDetailPanel from "../components/DistrictDetailPanel";
import { getPrediction, getGeoJSON, getCurrentStatus, getDiseases, getDistrictGeoJSON, getSpreadRisk, getAvailableYears } from "../services/api";

const MODE_LABELS = {
  current: { label: "District Actuals", icon: MapIcon, subtitle: "District Granularity" },
  predictive: { label: "AI Forecast", icon: BarChart3, subtitle: "AI District Forecast" },
  spread: { label: "Spread Map", icon: Wind, subtitle: "Disease Spread Vectors" },
};

const Dashboard = () => {
  const [year, setYear] = useState(null);
  const [viewMode, setViewMode] = useState("current");
  const [disease, setDisease] = useState("Dengue");
  const [diseasesList, setDiseasesList] = useState([]);
  const [yearsList, setYearsList] = useState([]);

  const [predictions, setPredictions] = useState([]);
  const [spreadVectors, setSpreadVectors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const [districtGeoData, setDistrictGeoData] = useState(null);

  // District Detail Panel state
  const [selectedDistrict, setSelectedDistrict] = useState(null);

  useEffect(() => {
    getDistrictGeoJSON().then(setDistrictGeoData).catch(err => console.error("Failed to fetch District Map:", err));
    getDiseases().then(res => setDiseasesList(res.diseases || [])).catch(err => console.error("Failed to fetch diseases", err));
    getAvailableYears().then(res => {
      const years = res.years || [];
      setYearsList(years);
      if (years.length > 0) setYear(years[years.length - 1]);
    }).catch(err => console.error("Failed to fetch years", err));
    getGeoJSON().catch(() => { });
  }, []);

  useEffect(() => {
    handleFetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, viewMode, disease]);

  const handleFetch = async () => {
    setLoading(true);
    setErrorMsg("");
    setPredictions([]);
    setSpreadVectors([]);

    try {
      if (viewMode === "predictive") {
        const data = await getPrediction(year, disease === "" ? null : disease);
        if (data.results?.error) {
          setErrorMsg(data.results.error);
        } else if (Array.isArray(data.results)) {
          setPredictions(data.results);
        }
      } else if (viewMode === "current") {
        const data = await getCurrentStatus(disease, year);
        if (data.region_data?.length > 0) {
          setPredictions(data.region_data);
        } else {
          setErrorMsg("No historical district outbreaks found for these filters.");
        }
      } else if (viewMode === "spread") {
        const [statusData, spreadData] = await Promise.all([
          getCurrentStatus(disease, year),
          getSpreadRisk(disease, year),
        ]);
        if (statusData.region_data?.length > 0) setPredictions(statusData.region_data);
        if (spreadData.vectors?.length > 0) {
          setSpreadVectors(spreadData.vectors);
        } else {
          setErrorMsg(spreadData.message || "No spread vectors detected for these filters.");
        }
      }
    } catch (error) {
      console.error("Fetch failed:", error);
      setErrorMsg(error.message || "Failed to fetch data.");
    } finally {
      setLoading(false);
    }
  };

  // Handle district click from map
  const handleDistrictClick = (state, district) => {
    setSelectedDistrict({ state, district });
  };

  const highCount = predictions.filter(p => p.risk === "High").length;
  const medCount = predictions.filter(p => p.risk === "Medium").length;
  const lowCount = predictions.filter(p => p.risk === "Low").length;
  const highSpread = spreadVectors.filter(v => v.spread_risk === "High").length;

  return (
    <div className="min-h-screen flex flex-col selection:bg-blue-500/30">
      {/* HEADER */}
      <header className="bg-white sticky top-0 z-20 border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-6 py-4 flex flex-wrap gap-4 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg border border-blue-100">
              <Satellite className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">SentinelGIS</h1>
              <p className="text-xs text-gray-500 font-medium uppercase tracking-widest">
                Geospatial Risk Intelligence
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="bg-gray-100 p-1 rounded-lg flex items-center border border-gray-200">
              {Object.entries(MODE_LABELS).map(([mode, { label, icon: Icon }]) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-4 py-2 rounded-md text-sm font-bold transition-all flex items-center gap-2 ${viewMode === mode
                      ? "bg-white text-blue-700 shadow-sm"
                      : "text-gray-500 hover:text-gray-700"
                    }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>

            {diseasesList.length > 0 && (
              <select
                value={disease}
                onChange={(e) => setDisease(e.target.value)}
                className="bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50 cursor-pointer font-medium text-sm"
              >
                <option value="">All Diseases</option>
                {diseasesList.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            )}

            <select
              value={year || ""}
              onChange={(e) => setYear(Number(e.target.value))}
              className="bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50 cursor-pointer font-medium text-sm"
            >
              {yearsList.map((y) => (
                <option key={y} value={y}>{y} Profile</option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {/* MAIN */}
      <main className="flex-1 container mx-auto px-6 py-8">
        {/* STATS ROW */}
        {(predictions.length > 0 || spreadVectors.length > 0) && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
          >
            {viewMode === "spread" ? (
              <>
                {[
                  { label: "High Spread Risk", count: highSpread, color: "text-red-600", border: "border-red-400", bg: "bg-red-50" },
                  { label: "Total Spread Vectors", count: spreadVectors.length, color: "text-amber-600", border: "border-amber-400", bg: "bg-amber-50" },
                  { label: "Origin Districts", count: new Set(spreadVectors.map(v => v.origin_district)).size, color: "text-blue-600", border: "border-blue-400", bg: "bg-blue-50" },
                ].map((stat) => (
                  <div key={stat.label} className={`glass-panel p-6 border-l-[4px] ${stat.border}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">{stat.label}</p>
                        <span className={`text-4xl font-bold ${stat.color} tracking-tight`}>{stat.count}</span>
                      </div>
                      <div className={`w-14 h-14 rounded-2xl ${stat.bg} flex items-center justify-center border border-gray-100`}>
                        <Wind className={`w-7 h-7 ${stat.color} opacity-80`} />
                      </div>
                    </div>
                  </div>
                ))}
              </>
            ) : (
              <>
                {[
                  { label: "High Risk Nodes", count: highCount, color: "text-red-600", border: "border-red-400", bg: "bg-red-50" },
                  { label: "Elevated Risk", count: medCount, color: "text-amber-600", border: "border-amber-400", bg: "bg-amber-50" },
                  { label: "Low Risk Base", count: lowCount, color: "text-emerald-600", border: "border-emerald-400", bg: "bg-emerald-50" },
                ].map((stat) => (
                  <div key={stat.label} className={`glass-panel p-6 border-l-[4px] ${stat.border}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">{stat.label}</p>
                        <span className={`text-4xl font-bold ${stat.color} tracking-tight`}>{stat.count}</span>
                      </div>
                      <div className={`w-14 h-14 rounded-2xl ${stat.bg} flex items-center justify-center border border-gray-100`}>
                        <Globe className={`w-7 h-7 ${stat.color} opacity-80`} />
                      </div>
                    </div>
                  </div>
                ))}
              </>
            )}
          </motion.div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-8">
          {/* MAP MODULE */}
          <div className="lg:col-span-8 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-3">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                </span>
                Spatial Risk Distribution ({MODE_LABELS[viewMode].subtitle})
              </h2>
            </div>
            <div className="glass-panel overflow-hidden p-1 shadow-sm relative">
              <MapView
                predictions={predictions}
                geoData={districtGeoData}
                viewMode={viewMode}
                spreadVectors={spreadVectors}
                onDistrictClick={handleDistrictClick}
              />
            </div>
            {viewMode !== "spread" && <Legend />}
            {viewMode === "spread" && (
              <div className="glass-panel p-4 flex flex-wrap gap-4 text-sm font-medium">
                <div className="flex items-center gap-2"><span className="w-4 h-0.5 bg-red-600 inline-block"></span>High Spread Risk</div>
                <div className="flex items-center gap-2"><span className="w-4 h-0.5 bg-amber-500 inline-block border-dashed border-t-2"></span>Medium Spread Risk</div>
                <div className="flex items-center gap-2"><span className="w-4 h-0.5 bg-emerald-600 inline-block border-dashed border-t-2"></span>Low Spread Risk</div>
                <p className="text-gray-400 text-xs">Arrows indicate direction from infected source → neighboring district</p>
              </div>
            )}
          </div>

          {/* SIDEBAR */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            <div className="flex items-center justify-between mt-1 border-b border-gray-200 pb-2">
              <h2 className="text-lg font-bold text-gray-900">
                {viewMode === "spread" ? "Spread Vectors" : "Assessment Log"}
              </h2>
              {(predictions.length > 0 || spreadVectors.length > 0) && (
                <span className="px-3 py-1 bg-gray-100 rounded-full text-xs font-semibold text-gray-600 border border-gray-200">
                  {viewMode === "spread" ? `${spreadVectors.length} vectors` : `${predictions.length} regions`}
                </span>
              )}
            </div>

            {(predictions.length === 0 && spreadVectors.length === 0) ? (
              <div className="glass-panel p-10 text-center flex flex-col items-center justify-center h-[520px] bg-gray-50/50">
                <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center mb-6 border border-gray-200 shadow-sm">
                  {loading ? <Loader2 className="w-8 h-8 text-blue-500 animate-spin" /> : <Globe className="w-8 h-8 text-gray-400" />}
                </div>
                {errorMsg ? (
                  <p className="text-sm text-red-600 font-medium bg-red-50 p-3 rounded-lg border border-red-100">{errorMsg}</p>
                ) : (
                  <>
                    <h3 className="text-gray-700 font-bold mb-2 text-lg">Loading Data…</h3>
                    <p className="text-sm text-gray-500 max-w-[250px] leading-relaxed">
                      Select temporal and disease parameters to map regional intelligence.
                    </p>
                  </>
                )}
              </div>
            ) : viewMode === "spread" ? (
              <div className="space-y-2 max-h-[520px] overflow-y-auto pr-2 pb-4 pt-2 custom-scrollbar">
                {spreadVectors.slice(0, 60).map((v, i) => {
                  const riskColors = { High: "border-red-400 bg-red-50", Medium: "border-amber-400 bg-amber-50", Low: "border-emerald-400 bg-emerald-50" };
                  const textColors = { High: "text-red-600", Medium: "text-amber-600", Low: "text-emerald-600" };
                  return (
                    <div key={i} className={`glass-panel p-3 border-l-[3px] ${riskColors[v.spread_risk] || "border-gray-300"}`}>
                      <p className="text-sm font-bold text-gray-800">
                        {v.origin_district} <span className="text-gray-400 font-normal">→</span> {v.dest_district}
                      </p>
                      <p className="text-xs text-gray-500">{v.origin_state}</p>
                      <p className={`text-xs font-bold mt-1 ${textColors[v.spread_risk] || "text-gray-500"}`}>
                        {v.spread_risk} Risk · {v.origin_cases} cases at source
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="space-y-3 max-h-[520px] overflow-y-auto pr-2 pb-4 pt-2 custom-scrollbar">
                {predictions.map((p, i) => (
                  <RiskCard
                    key={p.State + (p.District || "")}
                    state={`${p.District || p.state || "Unknown District"}, ${p.State || "Unknown State"}`}
                    risk={p.risk}
                    confidence={p.confidence}
                    index={i}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ─── ANALYTICS SECTION ─────────────────────────────────── */}
        <div className="border-t border-gray-200 pt-8 mt-4 space-y-8">
          <motion.h2
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-xl font-bold text-gray-900"
          >
            🔬 Advanced Analytics
          </motion.h2>

          {/* Row 1: Trend Chart + Anomaly Panel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TrendChart disease={disease || null} />
            <AnomalyPanel disease={disease || null} year={year} />
          </div>

          {/* Row 2: Co-occurrence Heatmap */}
          <CoOccurrenceHeatmap year={year} />
        </div>
      </main>

      {/* District Detail Slide-Out Panel */}
      {selectedDistrict && (
        <DistrictDetailPanel
          state={selectedDistrict.state}
          district={selectedDistrict.district}
          onClose={() => setSelectedDistrict(null)}
        />
      )}
    </div>
  );
};

export default Dashboard;