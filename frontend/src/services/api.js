const API_BASE = "http://127.0.0.1:8000";


// Predict risk using ML model
export async function getPrediction(year, disease) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ year, disease }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error("Prediction API failed: " + text);
  }

  return res.json();
}


// Fetch risk map data
export async function getRiskMap(year) {
  const res = await fetch(`${API_BASE}/risk-map?year=${year}`);

  if (!res.ok) {
    throw new Error("Risk map API failed");
  }

  return res.json();
}


export async function getGeoJSON() {
  const res = await fetch(`${API_BASE}/geojson`);

  if (!res.ok) {
    throw new Error("GeoJSON API failed");
  }

  return res.json();
}

export async function getDiseases() {
  const res = await fetch(`${API_BASE}/api/diseases`);
  if (!res.ok) throw new Error("Diseases API failed");
  return res.json();
}

export async function getAvailableYears() {
  const res = await fetch(`${API_BASE}/api/years`);
  if (!res.ok) throw new Error("Years API failed");
  return res.json();
}

export async function getCurrentStatus(disease, year) {
  let url = `${API_BASE}/api/current-status`;
  const params = new URLSearchParams();
  if (disease) params.append("disease", disease);
  if (year) params.append("year", year);
  
  if (params.toString()) url += `?${params.toString()}`;
  
  const res = await fetch(url);
  if (!res.ok) throw new Error("Current status API failed");
  return res.json();
}

export async function getDistrictGeoJSON() {
  const res = await fetch(`/india_districts.geojson`);
  if (!res.ok) throw new Error("District GeoJSON failed to load");
  return res.json();
}

export async function getSpreadRisk(disease, year) {
  let url = `${API_BASE}/api/spread-risk`;
  const params = new URLSearchParams();
  if (disease) params.append("disease", disease);
  if (year) params.append("year", year);
  if (params.toString()) url += `?${params.toString()}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Spread risk API failed");
  return res.json();
}

// ─── Advanced Analytics ─────────────────────────────────────────────────────

export async function getTrends(disease, state, district) {
  const params = new URLSearchParams();
  if (disease) params.append("disease", disease);
  if (state) params.append("state", state);
  if (district) params.append("district", district);
  const res = await fetch(`${API_BASE}/api/trends?${params.toString()}`);
  if (!res.ok) throw new Error("Trends API failed");
  return res.json();
}

export async function getAnomalies(disease, year) {
  const params = new URLSearchParams();
  if (disease) params.append("disease", disease);
  if (year) params.append("year", year);
  const res = await fetch(`${API_BASE}/api/anomalies?${params.toString()}`);
  if (!res.ok) throw new Error("Anomalies API failed");
  return res.json();
}

export async function getCoOccurrence(year) {
  const params = new URLSearchParams();
  if (year) params.append("year", year);
  const res = await fetch(`${API_BASE}/api/co-occurrence?${params.toString()}`);
  if (!res.ok) throw new Error("Co-occurrence API failed");
  return res.json();
}

export async function getCFR(disease, year) {
  const params = new URLSearchParams();
  if (disease) params.append("disease", disease);
  if (year) params.append("year", year);
  const res = await fetch(`${API_BASE}/api/cfr?${params.toString()}`);
  if (!res.ok) throw new Error("CFR API failed");
  return res.json();
}

export async function getDistrictDetail(state, district) {
  const params = new URLSearchParams({ state, district });
  const res = await fetch(`${API_BASE}/api/district-detail?${params.toString()}`);
  if (!res.ok) throw new Error("District detail API failed");
  return res.json();
}

// ─── Phase 4 Real-Time ──────────────────────────────────────────────────────

export async function getLiveAlerts() {
  const res = await fetch(`${API_BASE}/api/live/alerts`);
  if (!res.ok) throw new Error("Live alerts API failed");
  return res.json();
}

export async function getHealthAdvisor(disease, location) {
  const params = new URLSearchParams({ disease, location });
  const res = await fetch(`${API_BASE}/api/live/advisor?${params.toString()}`);
  if (!res.ok) throw new Error("Health advisor API failed");
  return res.json();
}

export async function getLiveSignals() {
  const res = await fetch(`${API_BASE}/api/live/signals`);
  if (!res.ok) throw new Error("Live signals API failed");
  return res.json();
}

export async function getLiveGeoAlerts() {
  const res = await fetch(`${API_BASE}/api/live/geo-alerts`);
  if (!res.ok) throw new Error("Live geo alerts API failed");
  return res.json();
}