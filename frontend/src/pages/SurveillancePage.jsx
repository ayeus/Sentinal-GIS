import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Globe, Loader2 } from "lucide-react";

import MapView from "../components/MapView";
import RiskCard from "../components/RiskCard";
import Legend from "../components/Legend";
import DistrictDetailPanel from "../components/DistrictDetailPanel";
import { getCurrentStatus, getDiseases, getDistrictGeoJSON, getAvailableYears } from "../services/api";

const SurveillancePage = () => {
  const [year, setYear] = useState(null);
  const [disease, setDisease] = useState("Dengue");
  const [diseasesList, setDiseasesList] = useState([]);
  const [yearsList, setYearsList] = useState([]);
  const [predictions, setPredictions] = useState([]);
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
    setLoading(true);
    setErrorMsg("");
    getCurrentStatus(disease, year)
      .then(data => {
        if (data.region_data?.length > 0) setPredictions(data.region_data);
        else setErrorMsg("No outbreaks found for these filters.");
      })
      .catch(err => setErrorMsg(err.message))
      .finally(() => setLoading(false));
  }, [year, disease]);

  const highCount = predictions.filter(p => p.risk === "High").length;
  const medCount = predictions.filter(p => p.risk === "Medium").length;
  const lowCount = predictions.filter(p => p.risk === "Low").length;

  return (
    <div className="container mx-auto px-6 py-8">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <h2 className="text-xl font-bold text-gray-900 flex-1">🗺️ District Surveillance</h2>
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
      {predictions.length > 0 && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[
            { label: "High Risk", count: highCount, color: "text-red-600", border: "border-red-400", bg: "bg-red-50" },
            { label: "Elevated Risk", count: medCount, color: "text-amber-600", border: "border-amber-400", bg: "bg-amber-50" },
            { label: "Low Risk", count: lowCount, color: "text-emerald-600", border: "border-emerald-400", bg: "bg-emerald-50" },
          ].map(stat => (
            <div key={stat.label} className={`glass-panel p-5 border-l-[4px] ${stat.border}`}>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-1">{stat.label}</p>
              <span className={`text-4xl font-bold ${stat.color}`}>{stat.count}</span>
            </div>
          ))}
        </motion.div>
      )}

      {/* Map + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 flex flex-col gap-4">
          <div className="glass-panel overflow-hidden p-1 shadow-sm">
            <MapView predictions={predictions} geoData={districtGeoData} viewMode="current"
              spreadVectors={[]} onDistrictClick={(s, d) => setSelectedDistrict({ state: s, district: d })} />
          </div>
          <Legend />
        </div>
        <div className="lg:col-span-4">
          <h3 className="text-lg font-bold text-gray-900 mb-3 border-b border-gray-200 pb-2">
            Assessment Log <span className="text-xs font-medium text-gray-400 ml-2">{predictions.length} regions</span>
          </h3>
          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>
          ) : errorMsg ? (
            <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg border border-red-100">{errorMsg}</p>
          ) : (
            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
              {predictions.map((p, i) => (
                <RiskCard key={p.State + (p.District || "")}
                  state={`${p.District || "Unknown"}, ${p.State}`}
                  risk={p.risk} confidence={p.confidence} index={i} />
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

export default SurveillancePage;
