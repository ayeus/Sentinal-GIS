import { createContext, lazy, Suspense, useCallback, useContext, useState } from "react";

// The panel (and its charts) is only downloaded when a district is first opened
const DistrictDetailPanel = lazy(() => import("../components/DistrictDetailPanel"));

const DistrictPanelContext = createContext({ openDistrict: () => {} });

/**
 * One district panel for the whole app: any map, list or the header search
 * can open it with openDistrict(state, district).
 */
export const DistrictPanelProvider = ({ children }) => {
  const [selected, setSelected] = useState(null);
  const openDistrict = useCallback((state, district) => {
    if (state && district) setSelected({ state, district });
  }, []);

  return (
    <DistrictPanelContext.Provider value={{ openDistrict }}>
      {children}
      {selected && (
        <Suspense fallback={null}>
          <DistrictDetailPanel state={selected.state} district={selected.district} onClose={() => setSelected(null)} />
        </Suspense>
      )}
    </DistrictPanelContext.Provider>
  );
};

const useDistrictPanel = () => useContext(DistrictPanelContext);

export default useDistrictPanel;
