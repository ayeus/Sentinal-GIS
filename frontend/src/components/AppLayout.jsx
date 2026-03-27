import { NavLink, Outlet } from "react-router-dom";
import { Satellite, Map as MapIcon, BrainCircuit, BarChart3, Radio } from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Surveillance", icon: MapIcon, description: "District Actuals" },
  { to: "/predictions", label: "Predictions", icon: BrainCircuit, description: "AI Forecast & Spread" },
  { to: "/analytics", label: "Analytics", icon: BarChart3, description: "Trends & Anomalies" },
  { to: "/live", label: "Live Intel", icon: Radio, description: "Real-Time Feed" },
];

const AppLayout = () => {
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

          {/* Navigation */}
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
        </div>
      </header>

      {/* PAGE CONTENT */}
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
};

export default AppLayout;
