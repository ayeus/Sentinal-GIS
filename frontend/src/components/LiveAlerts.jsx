import { useState, useEffect } from "react";
import { getLiveAlerts } from "../services/api";
import { Bell, ExternalLink, ShieldCheck, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const LiveAlerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = () => {
      getLiveAlerts()
        .then((res) => setAlerts(res || []))
        .catch(console.error)
        .finally(() => setLoading(false));
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-panel p-5 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4 border-b border-gray-100 pb-3">
        <h3 className="text-base font-bold text-gray-800 flex items-center gap-2">
          <div className="relative">
            <Bell className="w-4 h-4 text-blue-600" />
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full animate-ping"></span>
          </div>
          Live Intelligence Feed
        </h3>
        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded-full border border-blue-100 uppercase tracking-wider">
          Real-Time
        </span>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-3">
        {loading && alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-400">
            <Zap className="w-8 h-8 mb-2 animate-pulse" />
            <p className="text-xs font-medium uppercase tracking-widest">Scanning Global Feeds...</p>
          </div>
        ) : (
          <AnimatePresence>
            {alerts.map((alert, i) => (
              <motion.div
                key={alert.link + i}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className={`p-3 rounded-lg border-l-[3px] transition-all bg-white hover:shadow-md border border-gray-100 ${
                  alert.is_priority ? "border-l-blue-500 bg-blue-50/30" : "border-l-gray-300"
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <h4 className="text-xs font-bold text-gray-800 leading-tight">
                    {alert.title}
                  </h4>
                  <a href={alert.link} target="_blank" rel="noreferrer" className="text-gray-400 hover:text-blue-500 shrink-0">
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-gray-500 font-medium">
                  <span className="flex items-center gap-0.5 text-blue-600">
                    <ShieldCheck className="w-3 h-3" /> {alert.source}
                  </span>
                  <span>•</span>
                  <span>{alert.published}</span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
      
      <div className="mt-4 p-2 bg-gray-50 rounded-lg text-[10px] text-gray-400 flex items-center gap-2">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
        Tracking global pandemic signatures via WHO & News Feed API
      </div>
    </div>
  );
};

export default LiveAlerts;
