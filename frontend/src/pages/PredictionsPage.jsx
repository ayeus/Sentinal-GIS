import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { BrainCircuit, Wind, Loader2 } from "lucide-react";

import MapView from "../components/MapView";
import RiskCard from "../components/RiskCard";
import Legend from "../components/Legend";
import DistrictDetailPanel from "../components/DistrictDetailPanel";
import { getPrediction, getCurrentStatus, getDiseases, getDistrictGeoJSON, getSpreadRisk, getAvailableYears } from "../services/api";

const PredictionsPage = () => {
  const [year, setYear] = useState(null);
  const [mode, setMode] = useState("forecast"); // forecast | spread
  const [disease, setDisease] = useState("Dengue");
  const [diseasesList, setDiseasesList] = useState([]);
  const [yearsList, setYearsList] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [spreadVectors, setSpreadVectors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [districtGeoData, setDistrictGeoData] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);

  useEffect(() => {
    getDistrictGeoJSON().then(setDistrictGeoData).catch(console.error);
    getDiseases().then(res => setDiseasesList(res.diseases || [])).catch(console.error);
    getAvailableYears().then(res => {
      const years = res.years || [];
      setYearsList(years);
      if (years.length > 0) setYear(years[years.length - 1]);
    }).catch(console.error);

  }, []);

  useEffect(() => {
    if (!year) return;
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, disease, mode]);

  const fetchData = async () => {
    setLoading(true);
    setErrorMsg("");
    setPredictions([]);
    setSpreadVectors([]);
    try {
      if (mode === "forecast") {
        const data = await getPrediction(year, disease === "" ? null : disease);
        if (data.results?.error) setErrorMsg(data.results.error);
        else if (Array.isArray(data.results)) setPredictions(data.results);
      } else {
        const [statusData, spreadData] = await Promise.all([
          getCurrentStatus(disease, year),
          getSpreadRisk(disease, year),
        ]);
        if (statusData.region_data?.length > 0) setPredictions(statusData.region_data);
        if (spreadData.vectors?.length > 0) setSpreadVectors(spreadData.vectors);
        else setErrorMsg(spreadData.message || "No spread vectors detected.");
      }
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const highCount = predictions.filter(p => p.risk === "High").length;
  const isSpread = mode === "spread";

  return (
    <div className="container mx-auto px-6 py-8">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <h2 className="text-xl font-bold text-gray-900 flex-1 flex items-center gap-3">
          {isSpread ? "🌊 Disease Spread Prediction" : "🧠 AI Risk Forecast"}

        </h2>
        {/* Mode toggle */}
        <div className="bg-gray-100 p-1 rounded-lg flex border border-gray-200">
          <button onClick={() => setMode("forecast")}
            className={`px-4 py-2 rounded-md text-sm font-bold flex items-center gap-2 transition-all ${mode === "forecast" ? "bg-white text-purple-700 shadow-sm" : "text-gray-500"}`}>
            <BrainCircuit className="w-4 h-4" /> AI Forecast
          </button>
          <button onClick={() => setMode("spread")}
            className={`px-4 py-2 rounded-md text-sm font-bold flex items-center gap-2 transition-all ${mode === "spread" ? "bg-white text-orange-700 shadow-sm" : "text-gray-500"}`}>
            <Wind className="w-4 h-4" /> Spread Map
          </button>
        </div>
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

      {/* Stats */}
      {(predictions.length > 0 || spreadVectors.length > 0) && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {isSpread ? [
            { label: "High Spread Risk", count: spreadVectors.filter(v => v.spread_risk === "High").length, color: "text-red-600", border: "border-red-400" },
            { label: "Total Vectors", count: spreadVectors.length, color: "text-amber-600", border: "border-amber-400" },
            { label: "Origin Districts", count: new Set(spreadVectors.map(v => v.origin_district)).size, color: "text-blue-600", border: "border-blue-400" },
          ].map(s => (
            <div key={s.label} className={`glass-panel p-5 border-l-[4px] ${s.border}`}>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">{s.label}</p>
              <span className={`text-4xl font-bold ${s.color}`}>{s.count}</span>
            </div>
          )) : [
            { label: "High Risk", count: highCount, color: "text-red-600", border: "border-red-400" },
            { label: "Elevated", count: predictions.filter(p => p.risk === "Medium").length, color: "text-amber-600", border: "border-amber-400" },
            { label: "Low Risk", count: predictions.filter(p => p.risk === "Low").length, color: "text-emerald-600", border: "border-emerald-400" },
          ].map(s => (
            <div key={s.label} className={`glass-panel p-5 border-l-[4px] ${s.border}`}>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">{s.label}</p>
              <span className={`text-4xl font-bold ${s.color}`}>{s.count}</span>
            </div>
          ))}
        </motion.div>
      )}

      {/* Map + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 flex flex-col gap-4">
          <div className="glass-panel overflow-hidden p-1 shadow-sm">
            <MapView predictions={predictions} geoData={districtGeoData}
              viewMode={isSpread ? "spread" : "predictive"} spreadVectors={spreadVectors}
              liveSignals={{}}
              onDistrictClick={(s, d) => setSelectedDistrict({ state: s, district: d })} />
          </div>
          {isSpread ? (
            <div className="glass-panel p-4 flex flex-wrap gap-4 text-sm font-medium">
              <div className="flex items-center gap-2"><span className="w-4 h-0.5 bg-red-600 inline-block"></span>High</div>
              <div className="flex items-center gap-2"><span className="w-4 h-0.5 bg-amber-500 inline-block"></span>Medium</div>
              <div className="flex items-center gap-2"><span className="w-4 h-0.5 bg-emerald-600 inline-block"></span>Low</div>
              <p className="text-gray-400 text-xs">Arrows: Infected source → Neighboring district</p>
            </div>
          ) : <Legend />}
        </div>
        <div className="lg:col-span-4">
          <h3 className="text-lg font-bold text-gray-900 mb-3 border-b border-gray-200 pb-2 flex items-center justify-between">
            {isSpread ? "Spread Vectors" : "Forecast Log"}

          </h3>
          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>
          ) : errorMsg ? (
            <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg border border-red-100">{errorMsg}</p>
          ) : isSpread ? (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
              {spreadVectors.slice(0, 60).map((v, i) => {
                const rc = { High: "border-red-400 bg-red-50", Medium: "border-amber-400 bg-amber-50", Low: "border-emerald-400 bg-emerald-50" };
                const tc = { High: "text-red-600", Medium: "text-amber-600", Low: "text-emerald-600" };
                return (
                  <div key={i} className={`glass-panel p-3 border-l-[3px] ${rc[v.spread_risk] || ""}`}>
                    <p className="text-sm font-bold text-gray-800">{v.origin_district} → {v.dest_district}</p>
                    <p className={`text-xs font-bold mt-1 ${tc[v.spread_risk] || ""}`}>{v.spread_risk} · {v.origin_cases} cases</p>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
              {predictions.map((p, i) => (
                <RiskCard key={p.State + (p.District || "")}
                  state={`${p.District || "Unknown"}, ${p.State}`}
                  risk={p.risk} confidence={p.confidence} index={i}
                  />
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedDistrict && (
        <DistrictDetailPanel state={selectedDistrict.state} district={selectedDistrict.district}
          onClose={() => setSelectedDistrict(null)} />
      )}
    </div>
  );
};

export default PredictionsPage;
