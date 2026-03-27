import { useState, useEffect, useCallback, useRef } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { motion, AnimatePresence } from "framer-motion";
import { getLiveGeoAlerts } from "../services/api";
import { MapPin, X, ExternalLink, ShieldCheck, AlertTriangle, Radio, Flame } from "lucide-react";
// GeoJSON data is now fetched at runtime from public/data/india_states_full.geojson

const SEVERITY_CONFIG = {
  critical: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", badge: "bg-red-600", label: "CRITICAL" },
  high:     { bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700", badge: "bg-orange-500", label: "HIGH" },
  medium:   { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", badge: "bg-amber-500", label: "MEDIUM" },
  low:      { bg: "bg-yellow-50", border: "border-yellow-200", text: "text-yellow-700", badge: "bg-yellow-500", label: "LOW" },
};

const DISEASE_ICONS = {
  "Dengue": "🦟", "Malaria": "🦟", "Cholera": "💧", "Nipah": "🦇",
  "COVID-19": "🦠", "Influenza": "🤧", "Typhoid": "💧", "Chikungunya": "🦟",
  "Tuberculosis": "🫁", "Zika": "🦟", "Hepatitis": "🔬", "Measles": "💉",
  "Leptospirosis": "🐀", "Japanese Encephalitis": "🧠", "Plague": "☠️",
  "Ebola": "🩸", "HMPV": "🦠", "Outbreak Alert": "⚠️", "General Health Alert": "🏥",
};

const LiveIntelMap = () => {
  const [geoAlerts, setGeoAlerts] = useState(null);
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [geoLoading, setGeoLoading] = useState(true);
  const [selectedState, setSelectedState] = useState(null);
  const [selectedData, setSelectedData] = useState(null);
  const geoAlertsRef = useRef({});

  const fetchGeoAlerts = useCallback(() => {
    getLiveGeoAlerts()
      .then((res) => {
        const states = res.states || {};
        geoAlertsRef.current = states;
        setGeoAlerts(states);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // Fetch GeoJSON data from public folder
    fetch("/data/india_states_full.geojson")
      .then(res => res.json())
      .then(data => {
        setGeoData(data);
        setGeoLoading(false);
      })
      .catch(err => {
        console.error("Failed to load map regions:", err);
        setGeoLoading(false);
      });

    fetchGeoAlerts();
    const interval = setInterval(fetchGeoAlerts, 60000);
    return () => clearInterval(interval);
  }, [fetchGeoAlerts]);

  const normalize = (name) =>
    name?.toLowerCase().replace(/[^a-z ]/g, "").replace(/\s+/g, " ").trim();

  // Handle name differences between GeoJSON (older names) and backend
  const STATE_ALIASES = {
    "orissa": "odisha",
    "uttaranchal": "uttarakhand",
    "jammu and kashmir": "jammu kashmir",
  };

  const resolveAlias = (name) => {
    const n = normalize(name);
    return STATE_ALIASES[n] || n;
  };

  const getStateAlertData = useCallback((stateName) => {
    if (!stateName) return null;
    const alerts = geoAlertsRef.current;
    if (!alerts || Object.keys(alerts).length === 0) return null;
    const normName = resolveAlias(stateName);
    for (const [key, val] of Object.entries(alerts)) {
      if (resolveAlias(key) === normName) return val;
    }
    return null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getStateName = (feature) => {
    return feature.properties.NAME_1 || feature.properties.state || feature.properties.name || "Unknown";
  };

  const styleFeature = useCallback((feature) => {
    const stateName = getStateName(feature);
    const alertData = getStateAlertData(stateName);

    if (alertData) {
      return {
        fillColor: alertData.color || "#ef4444",
        weight: 3,
        color: "#ffffff",
        fillOpacity: 0.65,
        dashArray: "",
      };
    }
    return {
      fillColor: "#e2e8f0",
      weight: 1,
      color: "#94a3b8",
      fillOpacity: 0.35,
      dashArray: "",
    };
  }, [getStateAlertData]);

  const onEachFeature = useCallback((feature, layer) => {
    const stateName = getStateName(feature);
    const alertData = getStateAlertData(stateName);
    const count = alertData ? alertData.count : 0;
    const diseases = alertData?.danger_types || [];
    const diseaseStr = diseases.map(d => `${DISEASE_ICONS[d] || "⚠️"} ${d}`).join(", ");

    layer.bindTooltip(
      `<div style="font-family:'Outfit',sans-serif;padding:6px 10px;min-width:140px;">
        <strong style="font-size:13px;color:#0f172a;display:block;margin-bottom:3px;">${stateName}</strong>
        ${count > 0
          ? `<span style="color:#dc2626;font-weight:700;font-size:11px;display:block;margin-bottom:4px;">⚠ ${count} Alert${count > 1 ? "s" : ""}</span>
             <span style="color:#1e293b;font-size:11px;font-weight:600;">${diseaseStr}</span>`
          : `<span style="color:#64748b;font-size:11px;">No active alerts</span>`
        }
      </div>`,
      { sticky: true, direction: "top", className: "custom-tooltip" }
    );

    layer.on({
      mouseover: (e) => {
        e.target.setStyle({ weight: 4, color: "#0f172a", fillOpacity: 0.85 });
        e.target.bringToFront();
      },
      mouseout: (e) => {
        e.target.setStyle(styleFeature(feature));
      },
      click: () => {
        setSelectedState(stateName);
        setSelectedData(alertData);
      },
    });
  }, [getStateAlertData, styleFeature]);

  const totalAffected = geoAlerts ? Object.keys(geoAlerts).length : 0;
  const totalAlertCount = geoAlerts ? Object.values(geoAlerts).reduce((s, v) => s + v.count, 0) : 0;
  const severityInfo = selectedData ? SEVERITY_CONFIG[selectedData.severity] || SEVERITY_CONFIG.low : null;

  // Unique key that forces GeoJSON re-render when data arrives
  const geoKey = geoAlerts ? `geo-${Object.keys(geoAlerts).join("-")}-${totalAlertCount}` : "geo-loading";

  return (
    <div className="glass-panel overflow-hidden relative">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <MapPin className="w-5 h-5 text-red-500" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-ping"></span>
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-800">Live Threat Map — India</h3>
            <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">
              State-Level Intelligence • Click to Inspect Danger
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {totalAffected > 0 && (
            <span className="px-3 py-1 bg-red-50 text-red-700 text-[10px] font-bold rounded-full border border-red-200 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></span>
              {totalAffected} State{totalAffected !== 1 ? "s" : ""} • {totalAlertCount} Alert{totalAlertCount !== 1 ? "s" : ""}
            </span>
          )}
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-[10px] text-gray-400 font-medium">LIVE</span>
          </div>
        </div>
      </div>

      <div className="relative" style={{ height: "480px" }}>
        {(loading || geoLoading) ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 bg-gray-50">
            <Radio className="w-10 h-10 mb-3 animate-pulse text-red-400" />
            <p className="text-sm font-medium uppercase tracking-widest">
              {geoLoading ? "Loading Intelligence Map..." : "Fetching Live Signals..."}
            </p>
          </div>
        ) : (
          <MapContainer
            center={[22.5, 82]}
            zoom={5}
            style={{ height: "100%", width: "100%", background: "#f1f5f9" }}
            zoomControl={true}
            scrollWheelZoom={true}
          >
            <TileLayer
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png"
            />
            {geoData && (
              <GeoJSON
                key={geoKey}
                data={geoData}
                style={styleFeature}
                onEachFeature={onEachFeature}
              />
            )}
          </MapContainer>
        )}

        {/* Legend */}
        <div className="absolute bottom-4 left-4 z-[1000] bg-white/95 backdrop-blur-sm rounded-xl p-3 shadow-lg border border-gray-100">
          <p className="text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-2">Alert Severity</p>
          <div className="space-y-1.5">
            {[
              { color: "#dc2626", label: "Critical (5+)" },
              { color: "#ea580c", label: "High (3-4)" },
              { color: "#d97706", label: "Medium (2)" },
              { color: "#eab308", label: "Low (1)" },
              { color: "#e2e8f0", label: "No alerts" },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm border border-gray-200" style={{ backgroundColor: item.color }}></div>
                <span className="text-[10px] text-gray-600 font-medium">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* State Detail Panel */}
      <AnimatePresence>
        {selectedState && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute inset-x-0 bottom-0 z-[1001] m-4"
          >
            <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 max-h-[400px] overflow-hidden">
              {/* Panel Header */}
              <div className={`px-5 py-3 flex items-center justify-between border-b ${selectedData ? (severityInfo?.border || "border-gray-200") : "border-gray-200"} ${selectedData ? (severityInfo?.bg || "bg-gray-50") : "bg-gray-50"}`}>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-4 h-4 ${selectedData ? (severityInfo?.text || "text-gray-600") : "text-gray-400"}`} />
                    <h4 className="text-sm font-bold text-gray-900">{selectedState}</h4>
                  </div>
                  {selectedData ? (
                    <span className={`px-2 py-0.5 text-white text-[9px] font-bold rounded-full ${severityInfo?.badge || "bg-gray-500"}`}>
                      {severityInfo?.label || "UNKNOWN"} — {selectedData.count} ALERT{selectedData.count > 1 ? "S" : ""}
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 text-gray-600 text-[9px] font-bold rounded-full bg-gray-200">
                      NO ACTIVE ALERTS
                    </span>
                  )}
                </div>
                <button
                  onClick={() => { setSelectedState(null); setSelectedData(null); }}
                  className="w-7 h-7 rounded-full bg-white/80 hover:bg-gray-100 flex items-center justify-center transition-colors border border-gray-200"
                >
                  <X className="w-3.5 h-3.5 text-gray-500" />
                </button>
              </div>

              {selectedData ? (
                <>
                  {/* Danger Types Summary */}
                  {selectedData.danger_types?.length > 0 && (
                    <div className="px-5 py-3 bg-gradient-to-r from-red-50 to-orange-50 border-b border-red-100">
                      <p className="text-[10px] font-bold text-red-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <Flame className="w-3 h-3" /> Detected Threats
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedData.danger_types.map((d) => (
                          <span key={d} className="inline-flex items-center gap-1 px-2.5 py-1 bg-white rounded-full text-[11px] font-bold text-gray-800 border border-red-200 shadow-sm">
                            <span>{DISEASE_ICONS[d] || "⚠️"}</span> {d}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Alert List */}
                  <div className="p-4 space-y-2.5 max-h-[220px] overflow-y-auto custom-scrollbar">
                    {selectedData.alerts.map((alert, i) => (
                      <div
                        key={alert.link + i}
                        className="p-3 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-white hover:shadow-sm transition-all"
                      >
                        <div className="flex items-start justify-between gap-2 mb-1.5">
                          <h5 className="text-xs font-bold text-gray-800 leading-snug">{alert.title}</h5>
                          <a href={alert.link} target="_blank" rel="noreferrer"
                            className="text-gray-400 hover:text-blue-500 shrink-0 mt-0.5">
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                        {alert.summary && (
                          <p className="text-[11px] text-gray-500 leading-relaxed mb-1.5 line-clamp-2">{alert.summary}</p>
                        )}
                        <div className="flex items-center gap-2 text-[10px] text-gray-500 font-medium">
                          <span className="flex items-center gap-1 text-blue-600">
                            <ShieldCheck className="w-3 h-3" /> {alert.source}
                          </span>
                          <span>•</span>
                          <span>{alert.published}</span>
                          {alert.diseases?.length > 0 && (
                            <>
                              <span>•</span>
                              <span className="text-red-600 font-bold">{alert.diseases.map(d => DISEASE_ICONS[d] || "").join(" ")}</span>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="p-8 text-center text-gray-400">
                  <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-green-400" />
                  <p className="text-sm font-medium">No active disease alerts for {selectedState}</p>
                  <p className="text-xs text-gray-400 mt-1">This region is currently not flagged in any live news feeds</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default LiveIntelMap;
