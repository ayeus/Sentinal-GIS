import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

export const fetchGeoJSON = async () => {
  const res = await axios.get(`${API_BASE}/geojson`);
  return res.data;
};

export const fetchRiskMap = async (year) => {
  const res = await axios.get(`${API_BASE}/risk-map?year=${year}`);
  return res.data;
};
