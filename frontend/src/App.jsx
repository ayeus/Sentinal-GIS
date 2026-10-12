import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";

import AppLayout from "./components/AppLayout";
import { DataStatusProvider } from "./hooks/useDataStatus";
import { DistrictPanelProvider } from "./hooks/useDistrictPanel";

// Each page is loaded on first visit, keeping the initial download small
const SurveillancePage = lazy(() => import("./pages/SurveillancePage"));
const ForecastPage = lazy(() => import("./pages/ForecastPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const LivePage = lazy(() => import("./pages/LivePage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));

const PageLoading = () => (
  <div className="flex justify-center py-32"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>
);

function App() {
  return (
    <BrowserRouter>
      <DataStatusProvider>
        <DistrictPanelProvider>
          <Suspense fallback={<PageLoading />}>
            <Routes>
              <Route element={<AppLayout />}>
                <Route path="/" element={<SurveillancePage />} />
                <Route path="/forecast" element={<ForecastPage />} />
                <Route path="/predictions" element={<Navigate to="/forecast" replace />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/live" element={<LivePage />} />
                <Route path="/about" element={<AboutPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </Suspense>
        </DistrictPanelProvider>
      </DataStatusProvider>
    </BrowserRouter>
  );
}

export default App;
