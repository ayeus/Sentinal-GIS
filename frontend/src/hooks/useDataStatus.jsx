import { createContext, useContext, useEffect, useState } from "react";
import { getDataStatus } from "../services/api";

const DataStatusContext = createContext(null);

/** Loads /api/data-status once and shares it with every page. */
export const DataStatusProvider = ({ children }) => {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getDataStatus()
      .then(res => { if (!cancelled) { setStatus(res); setError(""); } })
      .catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [version]);

  return (
    <DataStatusContext.Provider value={{ status, error, refresh: () => setVersion(v => v + 1) }}>
      {children}
    </DataStatusContext.Provider>
  );
};

const useDataStatus = () => useContext(DataStatusContext) || { status: null, error: "", refresh: () => {} };

export default useDataStatus;
