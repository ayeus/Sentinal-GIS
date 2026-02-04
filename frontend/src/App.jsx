import { useEffect, useState } from "react";
import MapView from "./components/MapView";
import { fetchGeoJSON, fetchRiskMap } from "./api";

function App() {
  const [year, setYear] = useState(2023);
  const [geoData, setGeoData] = useState(null);
  const [riskData, setRiskData] = useState([]);

  // Load GeoJSON once
  useEffect(() => {
    fetchGeoJSON().then(setGeoData);
  }, []);

  // Load predictions on year change
  useEffect(() => {
    fetchRiskMap(year).then(setRiskData);
  }, [year]);

  if (!geoData) return <p>Loading map...</p>;

  return (
    <div style={{ padding: "1rem" }}>
      <h2>Dengue Risk Map — {year}</h2>

      <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
        <option value={2021}>2021</option>
        <option value={2022}>2022</option>
        <option value={2023}>2023</option>
      </select>

      <MapView geoData={geoData} riskData={riskData} />
    </div>
  );
}

export default App;
