import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Satellite, Map as MapIcon, BrainCircuit, BarChart3, Radio, Upload } from "lucide-react";
import { uploadPdf } from "../services/api";

const NAV_ITEMS = [
  { to: "/", label: "Surveillance", icon: MapIcon, description: "District Actuals" },
  { to: "/predictions", label: "Predictions", icon: BrainCircuit, description: "AI Forecast & Spread" },
  { to: "/analytics", label: "Analytics", icon: BarChart3, description: "Trends & Anomalies" },
  { to: "/live", label: "Live Intel", icon: Radio, description: "Real-Time Feed" },
];

const AppLayout = () => {
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [retrainResult, setRetrainResult] = useState(null);

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg("Extracting & Retraining...");
    try {
      const res = await uploadPdf(file);
      setRetrainResult(res);
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
      setUploadMsg("");
      e.target.value = "";
    }
  };

  return (
    <div className="min-h-screen flex flex-col selection:bg-blue-500/30">
      {/* GLOBAL HEADER */}
      <header className="bg-white sticky top-0 z-30 border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-6 py-3 flex items-center justify-between">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg border border-blue-100">
              <Satellite className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">SentinelGIS</h1>
              <p className="text-[10px] text-gray-500 font-medium uppercase tracking-widest">
                Epidemiological Intelligence Platform
              </p>
            </div>
          </div>

          {/* Navigation & Auto-Retrain Tool */}
          <div className="flex items-center gap-3">
            <nav className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl border border-gray-200">
              {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${
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

            {/* Ingest PDF & Auto-Retrain Button */}
            <label className={`cursor-pointer px-3 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border shadow-sm ${
              uploading
                ? "bg-purple-50 text-purple-700 border-purple-200 animate-pulse"
                : "bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-blue-500 hover:opacity-95"
            }`}>
              <Upload className="w-3.5 h-3.5" />
              {uploading ? uploadMsg || "Retraining..." : "Ingest PDF"}
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                disabled={uploading}
                onChange={handlePdfUpload}
              />
            </label>
          </div>
        </div>
      </header>

      {/* Auto-retrain Notification Toast */}
      {retrainResult && (
        <div className="bg-emerald-600 text-white px-6 py-2.5 text-xs font-bold flex items-center justify-between shadow-md">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-white animate-ping" />
            <span>
              {retrainResult.pipeline?.status === "retrained"
                ? `✅ PDF Processed! ${retrainResult.pipeline.new_records} new outbreak records extracted & ML model retrained (${retrainResult.pipeline.total_clean} total clean cases).`
                : `ℹ️ ${retrainResult.file}: ${retrainResult.pipeline?.message || "File registered."}`}
            </span>
          </div>
          <button onClick={() => setRetrainResult(null)} className="text-white/80 hover:text-white ml-4 text-sm font-bold">&times;</button>
        </div>
      )}


      {/* PAGE CONTENT */}
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
};

export default AppLayout;
