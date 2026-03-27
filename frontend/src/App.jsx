import { BrowserRouter, Routes, Route } from "react-router-dom";

import AppLayout from "./components/AppLayout";
import SurveillancePage from "./pages/SurveillancePage";
import PredictionsPage from "./pages/PredictionsPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import LivePage from "./pages/LivePage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<SurveillancePage />} />
          <Route path="/predictions" element={<PredictionsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/live" element={<LivePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
