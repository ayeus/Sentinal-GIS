import { useState, useEffect } from "react";
import { Radio, ExternalLink, BadgeCheck, Newspaper, Loader2 } from "lucide-react";
import { getLiveAlerts, getDiseases } from "../services/api";
import LiveIntelMap from "../components/LiveIntelMap";
import GuidancePanel from "../components/GuidancePanel";
import { LIVE_REFRESH_MS, DEFAULT_DISEASE, formatDate } from "../config";

const LivePage = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [indiaOnly, setIndiaOnly] = useState(true);
  const [diseasesList, setDiseasesList] = useState([]);
  const [guidanceDisease, setGuidanceDisease] = useState(DEFAULT_DISEASE);

  useEffect(() => {
    const fetchAlerts = () => {
      getLiveAlerts()
        .then(res => { setAlerts(res || []); setFailed(false); })
        .catch(err => { console.error(err); setFailed(true); })
        .finally(() => setLoading(false));
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, LIVE_REFRESH_MS);
    getDiseases().then(res => {
      const diseases = res.diseases || [];
      setDiseasesList(diseases);
      // Keep the select and the state in sync if the default is not in the dataset
      setGuidanceDisease(current => (diseases.includes(current) ? current : diseases[0] || ""));
    }).catch(console.error);
    return () => clearInterval(interval);
  }, []);

  const shown = indiaOnly ? alerts.filter(a => a.is_priority) : alerts;

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-2">
        <Radio className="w-6 h-6 text-red-500" />
        <h2 className="text-2xl font-bold text-gray-900">News &amp; official notices</h2>
      </div>
      <p className="text-sm text-gray-500 mb-6 max-w-4xl">
        Outbreak notices from the World Health Organization and recent news headlines, refreshed every few minutes.
        News items are <strong>media reports that have not been verified</strong>, and states are matched by the names
        mentioned in the text. Use them as leads to check, alongside the IDSP record on the other pages.
      </p>

      <div className="mb-8 relative">
        <LiveIntelMap />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* LEFT: feed */}
        <div className="lg:col-span-7">
          <div className="glass-panel p-5">
            <div className="flex flex-wrap items-center gap-3 mb-4 border-b border-gray-100 pb-3">
              <h3 className="text-base font-bold text-gray-800 flex-1">Latest reports</h3>
              <div className="flex gap-1 bg-gray-100 rounded-md p-0.5">
                {[[true, "India"], [false, "All"]].map(([value, label]) => (
                  <button key={label} onClick={() => setIndiaOnly(value)}
                    className={`px-3 py-1 rounded text-xs font-bold ${indiaOnly === value ? "bg-white text-blue-700 shadow-sm" : "text-gray-500"}`}>
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {loading ? (
              <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>
            ) : (
              <div className="space-y-3 max-h-[650px] overflow-y-auto pr-2 custom-scrollbar">
                {failed && (
                  <p className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg p-3">
                    The live feeds could not be reached. Items below, if any, are from the last successful fetch.
                  </p>
                )}
                {shown.length === 0 && !failed && (
                  <p className="text-sm text-gray-400 text-center py-12">
                    {indiaOnly ? "No current report mentions India or an Indian state." : "No reports available right now."}
                  </p>
                )}
                {shown.map((alert, i) => (
                  <div key={alert.link + i}
                    className={`p-4 rounded-xl border ${alert.official ? "border-blue-200 bg-blue-50/40" : "border-gray-200 bg-white"}`}>
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h4 className="text-sm font-bold text-gray-800 leading-snug">{alert.title}</h4>
                      <a href={alert.link} target="_blank" rel="noreferrer" aria-label="Open source"
                        className="text-gray-400 hover:text-blue-500 shrink-0 mt-0.5">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                    {alert.summary && <p className="text-xs text-gray-600 mb-2 leading-relaxed">{alert.summary}</p>}
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-500 font-semibold">
                      {alert.official ? (
                        <span className="flex items-center gap-1 text-blue-700"><BadgeCheck className="w-3.5 h-3.5" /> {alert.source} · official</span>
                      ) : (
                        <span className="flex items-center gap-1 text-gray-600"><Newspaper className="w-3.5 h-3.5" /> {alert.source} · unverified media report</span>
                      )}
                      <span>{alert.published_at ? formatDate(alert.published_at) : alert.published}</span>
                      {alert.locations?.length > 0 && <span className="text-gray-700">{alert.locations.join(", ")}</span>}
                      {alert.diseases?.length > 0 && <span className="text-rose-700">{alert.diseases.join(", ")}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: sourced guidance */}
        <div className="lg:col-span-5">
          <div className="glass-panel p-5 sticky top-36">
            <h3 className="text-base font-bold text-gray-800 mb-1">Disease guidance</h3>
            <p className="text-xs text-gray-500 mb-4">Summaries of WHO and CDC fact sheets, each linked to its source.</p>
            <select value={guidanceDisease} onChange={e => setGuidanceDisease(e.target.value)} aria-label="Disease"
              className="w-full bg-white border border-gray-300 rounded-lg px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-blue-500/50 focus:outline-none mb-4">
              {diseasesList.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
            <GuidancePanel disease={guidanceDisease} compact />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LivePage;
