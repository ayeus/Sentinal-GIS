import { Suspense, useState } from "react";
import { NavLink, Outlet, Link } from "react-router-dom";
import { Satellite, Map as MapIcon, BrainCircuit, BarChart3, Radio, Upload, Database, AlertTriangle, ServerCrash } from "lucide-react";
import { uploadPdf } from "../services/api";
import useDataStatus from "../hooks/useDataStatus";
import DistrictSearch from "./DistrictSearch";
import { formatDate } from "../config";

const NAV_ITEMS = [
  { to: "/", label: "Reported", icon: MapIcon, hint: "Outbreaks reported so far" },
  { to: "/forecast", label: "Forecast", icon: BrainCircuit, hint: "Where outbreaks are likely next" },
  { to: "/analytics", label: "Trends", icon: BarChart3, hint: "Trends and unusual counts" },
  { to: "/live", label: "News", icon: Radio, hint: "WHO notices and news headlines" },
  { to: "/about", label: "About the data", icon: Database, hint: "Sources, coverage and model test results" },
];

const AppLayout = () => {
  const [uploading, setUploading] = useState(false);
  const [retrainResult, setRetrainResult] = useState(null);
  const { status, error, refresh } = useDataStatus();

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await uploadPdf(file);
      setRetrainResult(res);
      refresh();
    } catch (err) {
      setRetrainResult({ file: file.name, pipeline: { status: "error", error: err.message } });
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  return (
    <div className="min-h-screen flex flex-col selection:bg-blue-500/30">
      {/* GLOBAL HEADER */}
      <header className="bg-white/90 backdrop-blur sticky top-0 z-30 border-b border-gray-200">
        <div className="container mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg border border-blue-100">
              <Satellite className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 leading-tight">SentinelGIS</h1>
              <p className="text-[10px] text-gray-500 font-medium uppercase tracking-widest">
                Disease outbreaks in India · reported &amp; forecast
              </p>
            </div>
          </Link>

          <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
            <DistrictSearch />
            <nav aria-label="Pages" className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl border border-gray-200 overflow-x-auto max-w-full">
              {NAV_ITEMS.map(({ to, label, icon: Icon, hint }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  title={hint}
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 whitespace-nowrap ${
                      isActive
                        ? "bg-white text-blue-700 shadow-sm border border-blue-100"
                        : "text-gray-500 hover:text-gray-700"
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </NavLink>
              ))}
            </nav>

            {/* Add a bulletin: extracts it, rebuilds the dataset and retrains the forecaster */}
            <label
              title="Upload an IDSP Weekly Outbreak Report (PDF). It is parsed, added to the dataset and the forecast is retrained."
              className={`cursor-pointer px-3 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border shadow-sm ${
                uploading
                  ? "bg-blue-50 text-blue-700 border-blue-200 animate-pulse"
                  : "bg-blue-600 text-white border-blue-600 hover:bg-blue-700"
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              {uploading ? "Uploading…" : "Add IDSP bulletin"}
              <input type="file" accept=".pdf" className="hidden" disabled={uploading} onChange={handlePdfUpload} />
            </label>
          </div>
        </div>
      </header>

      {/* Data currency: always visible, so an old bulletin is never mistaken for today's situation */}
      {error && (
        <div className="bg-red-600 text-white px-6 py-2 text-xs font-bold flex items-center gap-2">
          <ServerCrash className="w-4 h-4 shrink-0" />
          Cannot reach the SentinelGIS API ({error}). Nothing shown below is current.
        </div>
      )}
      {status && !status.available && (
        <div className="bg-amber-100 text-amber-900 px-6 py-2 text-xs font-bold flex items-center gap-2 border-b border-amber-200">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {status.message} Add an IDSP bulletin to begin.
        </div>
      )}
      {status?.available && (
        <div className={`px-6 py-2 text-xs flex flex-wrap items-center gap-x-4 gap-y-1 border-b ${
          status.is_stale ? "bg-amber-50 text-amber-900 border-amber-200" : "bg-emerald-50 text-emerald-900 border-emerald-200"
        }`}>
          <span className="flex items-center gap-2 font-bold">
            {status.is_stale
              ? <AlertTriangle className="w-4 h-4 shrink-0" />
              : <span className="w-2 h-2 rounded-full bg-emerald-500" />}
            {status.is_stale
              ? `Data is ${status.data_age_days} days old. This is not the current situation.`
              : "Data is current."}
          </span>
          <span>
            Latest IDSP bulletin: week {status.latest_week?.slice(6)} of {status.latest_week?.slice(0, 4)} (ending {formatDate(status.latest_week_end)})
          </span>
          <span className="text-gray-600">
            {status.bulletins_ingested} bulletins · {status.outbreaks.toLocaleString("en-IN")} reported outbreaks
          </span>
          <Link to="/about" className="font-bold underline underline-offset-2 ml-auto">Why? See sources &amp; limits</Link>
        </div>
      )}

      {/* Result of an upload */}
      {retrainResult && (
        <div className={`${retrainResult.pipeline?.status === "error" ? "bg-red-600" : "bg-blue-700"} text-white px-6 py-2.5 text-xs font-bold flex items-center justify-between shadow-md`}>
          <span>
            {retrainResult.pipeline?.status === "retrained"
              ? `${retrainResult.file}: ${retrainResult.pipeline.new_records} outbreak records extracted, forecast retrained (${retrainResult.pipeline.total_clean} outbreaks in the dataset). Reload the page to see them.`
              : retrainResult.pipeline?.status === "error"
              ? `${retrainResult.file}: ${retrainResult.pipeline.error || "Processing failed."}`
              : `${retrainResult.file}: ${retrainResult.pipeline?.message || "File saved."}`}
          </span>
          <button onClick={() => setRetrainResult(null)} className="text-white/80 hover:text-white ml-4 text-sm font-bold" aria-label="Dismiss">&times;</button>
        </div>
      )}

      {/* PAGE CONTENT */}
      <main className="flex-1">
        <Suspense fallback={<div className="py-32 text-center text-gray-400 text-sm">Loading…</div>}>
          <Outlet />
        </Suspense>
      </main>

      <footer className="border-t border-gray-200 bg-white">
        <div className="container mx-auto px-6 py-4 text-[11px] text-gray-500 leading-relaxed">
          Decision support only. Figures are outbreaks reported by States/UTs through the Integrated Disease Surveillance
          Programme (IDSP); unreported outbreaks are not shown. Forecasts are probabilities with known error rates
          (see <Link to="/about" className="underline">About the data</Link>) and do not replace field surveillance or
          the judgement of public-health officers.
        </div>
      </footer>
    </div>
  );
};

export default AppLayout;
