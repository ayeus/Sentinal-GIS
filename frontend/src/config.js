// Central frontend configuration. Every value can be overridden at build time
// with a REACT_APP_* variable (see .env.example); nothing else in src/ should
// hard-code a URL, map setting, interval or palette.

const env = process.env;

const num = (value, fallback) => {
  const parsed = Number(value);
  return value !== undefined && value !== "" && Number.isFinite(parsed) ? parsed : fallback;
};

// API base URL: custom URL via env var, localhost in dev, same-origin in prod
export const API_BASE = (
  env.REACT_APP_API_BASE !== undefined
    ? env.REACT_APP_API_BASE
    : (env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "")
).replace(/\/+$/, "");

// Sent as X-API-Key on admin calls when the backend sets ADMIN_API_KEY.
// Note: anything in a REACT_APP_* variable is public in the built bundle.
export const ADMIN_API_KEY = env.REACT_APP_ADMIN_API_KEY || "";

// Static map assets, resolved against PUBLIC_URL so sub-path deployments work
const publicUrl = (env.PUBLIC_URL || "").replace(/\/+$/, "");
export const DISTRICT_GEOJSON_URL = env.REACT_APP_DISTRICT_GEOJSON_URL || `${publicUrl}/india_districts.geojson`;
export const STATE_GEOJSON_URL = env.REACT_APP_STATE_GEOJSON_URL || `${publicUrl}/data/india_states_full.geojson`;

// Property keys holding the state / district names in the GeoJSON files
export const GEO_STATE_KEY = env.REACT_APP_GEO_STATE_KEY || "NAME_1";
export const GEO_DISTRICT_KEY = env.REACT_APP_GEO_DISTRICT_KEY || "NAME_2";

export const MAP = {
  center: [num(env.REACT_APP_MAP_CENTER_LAT, 22.9734), num(env.REACT_APP_MAP_CENTER_LNG, 78.6569)],
  districtZoom: num(env.REACT_APP_MAP_DISTRICT_ZOOM, 4.7),
  stateZoom: num(env.REACT_APP_MAP_STATE_ZOOM, 5),
  // Optional background tiles. Empty by default: the district and state
  // boundaries are the map, so it needs no third-party tile service or API key.
  tileUrl: env.REACT_APP_MAP_TILE_URL || "",
  tileAttribution: env.REACT_APP_MAP_TILE_ATTRIBUTION || "",
  attribution: 'Boundaries: <a href="https://www.geoboundaries.org" target="_blank" rel="noreferrer">geoBoundaries</a> (ODbL / CC BY)',
};

// How often the Live Intel views re-poll the backend
export const LIVE_REFRESH_MS = num(env.REACT_APP_LIVE_REFRESH_MS, 60000);

// Disease pre-selected in the filters ("" = all diseases); falls back to all
// when the dataset does not contain it
export const DEFAULT_DISEASE = env.REACT_APP_DEFAULT_DISEASE ?? "";

// Max spread vectors listed in the sidebar (the map always draws all of them)
export const SPREAD_LIST_LIMIT = num(env.REACT_APP_SPREAD_LIST_LIMIT, 60);

// Look-back choices (in reporting weeks, counted back from the newest bulletin)
export const RECENT_WEEK_OPTIONS = [4, 12, 26, 52];

// ─── Risk palette (shared by map, legend, cards, spread arrows) ─────────────
export const NO_DATA_COLOR = "#e5e7eb";

export const RISK_COLORS = {
  High: "#e11d48",
  Medium: "#f59e0b",
  Low: "#10b981",
  Minimal: "#cbd5e1",
};

export const getRiskColor = (risk) => RISK_COLORS[risk] || NO_DATA_COLOR;

export const SPREAD_COLORS = {
  High: RISK_COLORS.High,
  Medium: RISK_COLORS.Medium,
  Low: RISK_COLORS.Low,
};
export const SPREAD_FALLBACK_COLOR = "#64748b";

// ─── Formatting helpers ─────────────────────────────────────────────────────
export const formatDate = (iso) => {
  if (!iso) return "";
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
};

export const formatNumber = (value) => (value ?? 0).toLocaleString("en-IN");
export const formatPercent = (fraction, digits = 0) =>
  fraction === null || fraction === undefined ? "–" : `${(fraction * 100).toFixed(digits)}%`;
