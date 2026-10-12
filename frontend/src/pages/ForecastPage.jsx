import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { BrainCircuit, Share2, Loader2, AlertTriangle, FlaskConical } from "lucide-react";

import MapView from "../components/MapView";
import RiskCard from "../components/RiskCard";
import Legend from "../components/Legend";
import StatCard from "../components/StatCard";
import DistrictDetailPanel from "../components/DistrictDetailPanel";
import FilterBar from "../components/FilterBar";
import useSurveillanceFilters from "../hooks/useSurveillanceFilters";
import { getForecast, getCurrentStatus, getDistrictGeoJSON, getSpreadRisk } from "../services/api";
import { SPREAD_LIST_LIMIT, formatDate, formatNumber, formatPercent } from "../config";

const TIER_STYLE = {
  High: { border: "border-rose-400", tone: "text-rose-600" },
  Medium: { border: "border-amber-400", tone: "text-amber-600" },
  Low: { border: "border-emerald-400", tone: "text-emerald-600" },
};

// The facts behind a forecast row, in plain words
const facts = (row) => {
  const list = [
    row.outbreaks_52w > 0
      ? `${row.outbreaks_52w} outbreak${row.outbreaks_52w === 1 ? "" : "s"} here in the past year`
      : "none reported here in the past year",
  ];
  if (row.neighbour_outbreaks_12w > 0) list.push(`${row.neighbour_outbreaks_12w} in neighbouring districts (12 wks)`);
  if (row.state_outbreaks_12w > 0) list.push(`${row.state_outbreaks_12w} in the state (12 wks)`);
  return list;
};

const ForecastPage = () => {
  const filters = useSurveillanceFilters();
  const { disease, period, modelledDiseases } = filters;
  const [mode, setMode] = useState("forecast"); // forecast | exposure
  const [forecast, setForecast] = useState(null);
  const [exposure, setExposure] = useState({ rows: [], vectors: [], message: "" });
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [districtGeoData, setDistrictGeoData] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const isExposure = mode === "exposure";

  useEffect(() => {
    getDistrictGeoJSON().then(setDistrictGeoData).catch(console.error);
  }, []);

  useEffect(() => {
    if (isExposure && !period) return;
    // Ignore responses that arrive after the filters changed again
    let cancelled = false;
    setLoading(true);
    setErrorMsg("");

    const load = isExposure
      ? Promise.all([getCurrentStatus(disease, period), getSpreadRisk(disease, period)]).then(([statusData, spreadData]) => {
          if (cancelled) return;
          setExposure({
            rows: statusData.region_data || [],
            vectors: spreadData.vectors || [],
            message: spreadData.vectors?.length ? "" : (spreadData.error || spreadData.message || "No neighbouring districts are exposed for these filters."),
          });
        })
      : getForecast(disease).then(res => { if (!cancelled) setForecast(res); });

    load.catch(err => { if (!cancelled) setErrorMsg(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [disease, period, isExposure]);

  // One entry per source district, with the districts it borders
  const sources = useMemo(() => {
    const bySource = new Map();
    exposure.vectors.forEach(v => {
      const key = `${v.origin_state}|${v.origin_district}`;
      if (!bySource.has(key)) bySource.set(key, { ...v, neighbours: [] });
      bySource.get(key).neighbours.push(v.dest_state === v.origin_state ? v.dest_district : `${v.dest_district} (${v.dest_state})`);
    });
    return [...bySource.values()].sort((a, b) => b.origin_cases - a.origin_cases);
  }, [exposure.vectors]);

  const window_ = forecast?.window;
  const results = forecast?.results || [];
  const tierInfo = Object.fromEntries((forecast?.tiers || []).map(t => [t.tier, t]));

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="flex flex-wrap items-center gap-4 mb-2">
        <h2 className="text-xl font-bold text-gray-900 flex-1">
          {isExposure ? "Districts bordering an outbreak" : "Outbreak forecast"}
        </h2>
        <div className="bg-gray-100 p-1 rounded-lg flex border border-gray-200">
          <button onClick={() => setMode("forecast")}
            className={`px-4 py-2 rounded-md text-sm font-bold flex items-center gap-2 transition-all ${!isExposure ? "bg-white text-blue-700 shadow-sm" : "text-gray-500"}`}>
            <BrainCircuit className="w-4 h-4" /> Forecast
          </button>
          <button onClick={() => setMode("exposure")}
            className={`px-4 py-2 rounded-md text-sm font-bold flex items-center gap-2 transition-all ${isExposure ? "bg-white text-blue-700 shadow-sm" : "text-gray-500"}`}>
            <Share2 className="w-4 h-4" /> Neighbour exposure
          </button>
        </div>
        <FilterBar {...filters} showPeriod={isExposure}
          diseasesList={isExposure ? filters.diseasesList : modelledDiseases} />
      </div>

      {isExposure ? (
        <p className="text-sm text-gray-500 mb-6">
          For each district that reported an outbreak in the selected period, the districts sharing a border with it.
          This is geographic proximity, <strong>not a prediction</strong>; diseases that do not pass between districts
          (such as food poisoning) are excluded.
        </p>
      ) : (
        <p className="text-sm text-gray-500 mb-6">
          Probability that IDSP reports at least one outbreak in a district
          {window_ ? <> between <strong>{formatDate(window_.window_start)}</strong> and <strong>{formatDate(window_.window_end)}</strong></> : null},
          estimated from bulletins up to {window_ ? formatDate(window_.based_on_week_end) : "the latest week"}.
          {!disease && " With all diseases selected, each district shows its highest-probability disease."}
        </p>
      )}

      {/* The forecast window has passed: say so before anything else */}
      {!isExposure && window_ && window_.status === "expired" && (
        <div className="mb-6 p-4 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 flex gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="text-sm leading-relaxed">
            <strong>This forecast window ended {window_.days_since_window_end} days ago.</strong> The newest bulletin
            in the system is from {formatDate(window_.based_on_week_end)}. Add the recent IDSP bulletins (they are
            fetched automatically when the IDSP portal is reachable, or use “Add IDSP bulletin”) to produce a forecast
            for the coming weeks. Until then, treat this page as a record of what the model said, not as current guidance.
          </div>
        </div>
      )}

      {!isExposure && forecast && !forecast.available && (
        <div className="mb-6 p-4 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-700">{forecast.message}</div>
      )}

      {/* Stats */}
      {isExposure ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard label="Source districts" value={sources.length} border="border-blue-400" tone="text-blue-700" />
          <StatCard label="Bordering districts" value={new Set(exposure.vectors.map(v => `${v.dest_state}|${v.dest_district}`)).size} border="border-amber-400" tone="text-amber-700" />
          <StatCard label="Large sources (>100 cases)" value={sources.filter(v => v.spread_risk === "High").length} border="border-rose-400" tone="text-rose-700" />
        </div>
      ) : forecast?.available && forecast.modelled !== false && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {["High", "Medium", "Low"].map(tier => (
            <StatCard key={tier}
              label={`${tier} risk districts`}
              value={forecast.tier_counts?.[tier] ?? 0}
              border={TIER_STYLE[tier].border} tone={TIER_STYLE[tier].tone}
              hint={tierInfo[tier]?.observed_outbreak_rate != null
                ? `In testing, ${formatPercent(tierInfo[tier].observed_outbreak_rate)} of ${tier} flags were followed by a reported outbreak.`
                : undefined} />
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 flex flex-col gap-4">
          <div className="glass-panel overflow-hidden p-1 shadow-sm">
            {isExposure ? (
              <MapView rows={exposure.rows} geoData={districtGeoData} spreadVectors={exposure.vectors}
                describe={(row) => [`${formatNumber(row.Cases)} cases reported`, row.Diseases]}
                emptyLabel="No outbreak reported in this period"
                onDistrictClick={(state, district) => setSelectedDistrict({ state, district })} />
            ) : (
              <MapView rows={results} geoData={districtGeoData}
                describe={(row) => [`${row.risk} risk: ${formatPercent(row.probability)} chance`, row.Disease, ...facts(row)]}
                emptyLabel="Minimal risk (below 3%)"
                onDistrictClick={(state, district) => setSelectedDistrict({ state, district })} />
            )}
          </div>
          {isExposure ? (
            <Legend title="Cases at the source" emptyLabel="None reported"
              items={[{ risk: "High", label: "More than 100" }, { risk: "Medium", label: "16 to 100" }, { risk: "Low", label: "6 to 15" }]}
              note="Lines connect a district with a reported outbreak to each district it borders. Sources with 5 or fewer cases are not drawn." />
          ) : (
            <Legend title="Forecast probability" emptyLabel="Minimal"
              items={(forecast?.tiers || []).filter(t => t.tier !== "Minimal").map(t => ({
                risk: t.tier, label: t.tier, hint: `${formatPercent(t.min_probability)} or more`,
              }))}
              note="A forecast is a probability, not a certainty. Districts shown as Minimal are not risk-free: in testing, a sizeable share of outbreaks occurred there." />
          )}

          {!isExposure && forecast?.available && (
            <div className="glass-panel p-4 flex gap-3 items-start">
              <FlaskConical className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <p className="text-xs text-gray-600 leading-relaxed">
                <strong className="text-gray-800">How far to trust this.</strong> The model was tested on recent weeks it
                had never seen. Its risk tiers behaved as labelled there, but most flags, even High ones, were not
                followed by a reported outbreak, and it only knows about outbreaks that were reported to IDSP.{" "}
                <Link to="/about" className="text-blue-700 font-bold underline underline-offset-2">See the full test results and limitations</Link>.
              </p>
            </div>
          )}
        </div>

        <div className="lg:col-span-4">
          <h3 className="text-lg font-bold text-gray-900 mb-3 border-b border-gray-200 pb-2">
            {isExposure ? "Source districts" : "Highest risk first"}
            <span className="text-xs font-medium text-gray-400 ml-2">
              {isExposure ? `${sources.length} · most cases first` : `${results.length} districts above Minimal`}
            </span>
          </h3>
          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>
          ) : errorMsg ? (
            <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg border border-red-100">{errorMsg}</p>
          ) : isExposure ? (
            exposure.vectors.length === 0 ? (
              <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg border border-gray-200">{exposure.message}</p>
            ) : (
              <div className="space-y-2 max-h-[640px] overflow-y-auto pr-2 custom-scrollbar">
                {sources.slice(0, SPREAD_LIST_LIMIT).map(source => (
                  <RiskCard key={`${source.origin_state}|${source.origin_district}`}
                    title={source.origin_district} subtitle={source.origin_state}
                    risk={source.spread_risk} value={formatNumber(source.origin_cases)} valueLabel="cases reported"
                    facts={[`Borders ${source.neighbours.join(", ")}`]}
                    onClick={() => setSelectedDistrict({ state: source.origin_state, district: source.origin_district })} />
                ))}
                {sources.length > SPREAD_LIST_LIMIT && (
                  <p className="text-xs text-gray-400 text-center py-2">Showing the {SPREAD_LIST_LIMIT} largest sources; all are drawn on the map.</p>
                )}
              </div>
            )
          ) : results.length === 0 ? (
            <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg border border-gray-200">
              {forecast?.message || "No district is above the Minimal tier for this disease in this window."}
            </p>
          ) : (
            <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-2 custom-scrollbar">
              {results.map(row => (
                <RiskCard key={`${row.State}|${row.District}|${row.Disease}`}
                  title={row.District} subtitle={row.State} risk={row.risk}
                  caption={`${row.risk} · ${row.Disease}`}
                  value={formatPercent(row.probability)} valueLabel="probability"
                  facts={facts(row)}
                  onClick={() => setSelectedDistrict({ state: row.State, district: row.District })} />
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

export default ForecastPage;
