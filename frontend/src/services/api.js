import { API_BASE, ADMIN_API_KEY, DISTRICT_GEOJSON_URL, STATE_GEOJSON_URL } from "../config";

// Shared request helper: builds the query string (skipping empty values),
// and surfaces the backend's error detail when a call fails.
async function request(path, { params, label = "API", ...options } = {}) {
  const query = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.append(key, value);
  });
  const qs = query.toString();

  const res = await fetch(`${API_BASE}${path}${qs ? `?${qs}` : ""}`, options);
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.clone().json();
      detail = typeof body.detail === "string" ? body.detail : "";
    } catch {
      detail = await res.text().catch(() => "");
    }
    throw new Error(detail || `${label} failed (${res.status})`);
  }
  return res.json();
}

const adminHeaders = () => (ADMIN_API_KEY ? { "X-API-Key": ADMIN_API_KEY } : {});

// Boundary files are large and never change during a session: fetch each once
const staticCache = new Map();
function fetchStatic(url, label) {
  if (!staticCache.has(url)) {
    const pending = fetch(url).then(res => {
      if (!res.ok) throw new Error(`${label} failed to load`);
      return res.json();
    });
    pending.catch(() => staticCache.delete(url));
    staticCache.set(url, pending);
  }
  return staticCache.get(url);
}


// ─── Surveillance (reported outbreaks) ──────────────────────────────────────
// `period` is { year } or { weeks } (latest N reporting weeks)

export const getDataStatus = () => request("/api/data-status", { label: "Data status API" });
export const getDiseases = () => request("/api/diseases", { label: "Diseases API" });
export const getAvailableYears = () => request("/api/years", { label: "Years API" });

export const getCurrentStatus = (disease, period) =>
  request("/api/current-status", { params: { disease, ...period }, label: "Surveillance API" });

export const getDistrictGeoJSON = () => fetchStatic(DISTRICT_GEOJSON_URL, "District GeoJSON");
export const getStateGeoJSON = () => fetchStatic(STATE_GEOJSON_URL, "State GeoJSON");

export const getSpreadRisk = (disease, period) =>
  request("/api/spread-risk", { params: { disease, ...period }, label: "Neighbour exposure API" });

// ─── Forecast ───────────────────────────────────────────────────────────────

export const getForecast = (disease) =>
  request("/api/forecast", { params: { disease }, label: "Forecast API" });

// Every forecast disease for one district
export const getDistrictForecast = (state, district) =>
  request("/api/forecast", { params: { state, district }, label: "Forecast API" });

export const getModelCard = () => request("/api/model-card", { label: "Model card API" });

// ─── Analytics ──────────────────────────────────────────────────────────────

export const getTrends = (disease, state, district) =>
  request("/api/trends", { params: { disease, state, district }, label: "Trends API" });

export const getAnomalies = (disease, period) =>
  request("/api/anomalies", { params: { disease, ...period }, label: "Anomalies API" });

export const getCoOccurrence = (period) =>
  request("/api/co-occurrence", { params: { ...period }, label: "Co-occurrence API" });

export const getCFR = (disease, period) =>
  request("/api/cfr", { params: { disease, ...period }, label: "CFR API" });

export const getDistrictDetail = (state, district) =>
  request("/api/district-detail", { params: { state, district }, label: "District detail API" });

// ─── Live signals ───────────────────────────────────────────────────────────

export const getLiveAlerts = () => request("/api/live/alerts", { label: "Live alerts API" });
export const getLiveGeoAlerts = () => request("/api/live/geo-alerts", { label: "Live geo alerts API" });

export const getGuidance = (disease) =>
  request("/api/live/guidance", { params: { disease }, label: "Guidance API" });

// ─── Admin ──────────────────────────────────────────────────────────────────

export function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/upload-pdf", {
    label: "PDF upload and auto-retrain",
    method: "POST",
    headers: adminHeaders(),
    body: formData,
  });
}

export const triggerPipeline = () =>
  request("/api/admin/trigger-pipeline", { label: "Trigger pipeline", method: "POST", headers: adminHeaders() });
