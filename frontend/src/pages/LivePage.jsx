import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Radio, ExternalLink, ShieldCheck, AlertCircle, ShieldAlert, Sparkles, BrainCircuit, Zap } from "lucide-react";
import { getLiveAlerts, getHealthAdvisor, getDiseases } from "../services/api";
import LiveIntelMap from "../components/LiveIntelMap";

const LivePage = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [diseasesList, setDiseasesList] = useState([]);

  // AI Advisor state
  const [advDisease, setAdvDisease] = useState("Dengue");
  const [advLocation, setAdvLocation] = useState("");
  const [advisor, setAdvisor] = useState(null);
  const [advLoading, setAdvLoading] = useState(false);

  useEffect(() => {
    const fetchAlerts = () => {
      getLiveAlerts()
        .then(res => setAlerts(res || []))
        .catch(console.error)
        .finally(() => setLoading(false));
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000);
    getDiseases().then(res => setDiseasesList(res.diseases || [])).catch(console.error);
    return () => clearInterval(interval);
  }, []);

  const fetchAdvisor = () => {
    if (!advDisease || !advLocation) return;
    setAdvLoading(true);
    getHealthAdvisor(advDisease, advLocation)
      .then(setAdvisor)
      .catch(console.error)
      .finally(() => setAdvLoading(false));
  };

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="relative">
          <Radio className="w-6 h-6 text-red-500" />
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping"></span>
        </div>
        <h2 className="text-xl font-bold text-gray-900">Live Intelligence Center</h2>
        <span className="px-3 py-1 bg-red-50 text-red-700 text-xs font-bold rounded-full border border-red-200 uppercase tracking-wider">
          Real-Time
        </span>
      </div>

      {/* ─── Live Threat Map ─────────────────────────────────────── */}
      <div className="mb-8 relative">
        <LiveIntelMap />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* LEFT: News Feed */}
        <div className="lg:col-span-7">
          <div className="glass-panel p-5">
            <h3 className="text-base font-bold text-gray-800 mb-4 flex items-center gap-2 border-b border-gray-100 pb-3">
              📡 Global Disease Alert Feed
              <span className="text-[10px] text-gray-400 font-medium uppercase ml-auto">WHO + Google News</span>
            </h3>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                <Zap className="w-10 h-10 mb-3 animate-pulse" />
                <p className="text-sm font-medium uppercase tracking-widest">Scanning Global Feeds...</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[650px] overflow-y-auto pr-2 custom-scrollbar">
                {alerts.map((alert, i) => (
                  <motion.div key={alert.link + i}
                    initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className={`p-4 rounded-xl border transition-all hover:shadow-md ${
                      alert.is_priority
                        ? "border-blue-200 bg-blue-50/40 border-l-[4px] border-l-blue-500"
                        : "border-gray-100 bg-white"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h4 className="text-sm font-bold text-gray-800 leading-snug">{alert.title}</h4>
                      <a href={alert.link} target="_blank" rel="noreferrer"
                        className="text-gray-400 hover:text-blue-500 shrink-0 mt-0.5">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                    {alert.summary && (
                      <p className="text-xs text-gray-500 mb-2 leading-relaxed">{alert.summary}</p>
                    )}
                    <div className="flex items-center gap-3 text-[10px] text-gray-500 font-semibold">
                      <span className="flex items-center gap-1 text-blue-600">
                        <ShieldCheck className="w-3 h-3" /> {alert.source}
                      </span>
                      <span>•</span>
                      <span>{alert.published}</span>
                      {alert.is_priority && (
                        <span className="ml-auto px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-[9px] font-bold uppercase">
                          India Priority
                        </span>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: AI Health Advisor */}
        <div className="lg:col-span-5">
          <div className="glass-panel p-5 sticky top-24">
            <h3 className="text-base font-bold text-gray-800 flex items-center gap-2 mb-4 border-b border-gray-100 pb-3">
              <BrainCircuit className="w-5 h-5 text-purple-600" />
              AI Health Advisor
            </h3>

            <div className="space-y-3 mb-5">
              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1 block">Disease</label>
                <select value={advDisease} onChange={e => setAdvDisease(e.target.value)}
                  className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-purple-500/50 focus:outline-none">
                  {diseasesList.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1 block">Location / District</label>
                <input type="text" placeholder="e.g. Dehradun"
                  value={advLocation} onChange={e => setAdvLocation(e.target.value)}
                  className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-purple-500/50 focus:outline-none"
                  onKeyDown={e => e.key === "Enter" && fetchAdvisor()}
                />
              </div>
              <button onClick={fetchAdvisor} disabled={advLoading || !advLocation}
                className="w-full py-2.5 bg-purple-600 text-white rounded-lg font-bold text-sm hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                <Sparkles className="w-4 h-4" />
                {advLoading ? "Analyzing..." : "Get AI Advisory"}
              </button>
            </div>

            {advisor && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="space-y-3 pt-4 border-t border-gray-100">
                <div className="bg-amber-50/60 border border-amber-100 rounded-xl p-3">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-amber-700 uppercase mb-1">
                    <AlertCircle className="w-3 h-3" /> Probable Cause
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed font-medium">{advisor.causes}</p>
                </div>
                <div className="bg-emerald-50/60 border border-emerald-100 rounded-xl p-3">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-700 uppercase mb-1">
                    <ShieldAlert className="w-3 h-3" /> Prevention & Safety
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed font-medium">{advisor.prevention}</p>
                </div>
                <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-3">
                  <div className="flex items-center gap-2 text-[10px] font-bold text-blue-700 uppercase mb-1">
                    <Sparkles className="w-3 h-3" /> Clinical Suggestion
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed font-medium">{advisor.suggestion}</p>
                </div>
                <p className="text-[10px] text-gray-400 text-center pt-2">
                  Advisory for <strong>{advisor.disease}</strong> in <strong>{advisor.location}</strong> • {advisor.timestamp}
                </p>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LivePage;
