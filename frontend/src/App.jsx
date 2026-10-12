import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import AppLayout from "./components/AppLayout";
import { DataStatusProvider } from "./hooks/useDataStatus";
import SurveillancePage from "./pages/SurveillancePage";
import ForecastPage from "./pages/ForecastPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import LivePage from "./pages/LivePage";
import AboutPage from "./pages/AboutPage";

function App() {
  return (
    <BrowserRouter>
      <DataStatusProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<SurveillancePage />} />
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/predictions" element={<Navigate to="/forecast" replace />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/live" element={<LivePage />} />
            <Route path="/about" element={<AboutPage />} />
          </Route>
        </Routes>
      </DataStatusProvider>
    </BrowserRouter>
  );
}

export default App;
