import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, AttributionControl } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import SpreadArrows from "./SpreadArrows";
import { getStateGeoJSON } from "../services/api";
import { MAP, GEO_STATE_KEY, GEO_DISTRICT_KEY, getRiskColor } from "../config";

const STATE_OUTLINE = { fill: false, color: "#475569", weight: 1.1, opacity: 0.9, interactive: false };

const normalize = (name) =>
  name?.toLowerCase().replace(/[^a-z0-9]/g, "").trim();

const escapeHtml = (text) =>
  String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/**
 * District choropleth. `rows` are records with State, District and `risk`
 * (High | Medium | Low | Minimal); `describe(row)` returns the text lines
 * shown in a district's popup; `emptyLabel` is shown for districts without a row.
 */
const MapView = ({ rows = [], geoData, spreadVectors = [], onDistrictClick, describe, emptyLabel = "Nothing reported" }) => {
  const [stateGeo, setStateGeo] = useState(null);
  useEffect(() => {
    getStateGeoJSON().then(setStateGeo).catch(console.error);
  }, []);

  // (state, district) -> row, built once per result set instead of scanning per polygon
  const rowsByDistrict = useMemo(() => {
    const index = new Map();
    rows.forEach(row => index.set(`${normalize(row.State)}|${normalize(row.District)}`, row));
    return index;
  }, [rows]);

  const getMatch = (feature) =>
    rowsByDistrict.get(`${normalize(feature.properties[GEO_STATE_KEY])}|${normalize(feature.properties[GEO_DISTRICT_KEY])}`);

  const style = (feature) => {
    const row = getMatch(feature);
    return {
      fillColor: getRiskColor(row?.risk),
      weight: row ? 1 : 0.6,
      color: row ? "#ffffff" : "#cbd5e1",
      fillOpacity: row ? 0.85 : 0.45,
    };
  };

  const onEachFeature = (feature, layer) => {
    const row = getMatch(feature);
    const stateName = feature.properties[GEO_STATE_KEY] || "";
    const districtName = feature.properties[GEO_DISTRICT_KEY] || "Unknown district";

    layer.on({
      mouseover: (e) => {
        e.target.setStyle({ weight: 3, color: "#0f172a", fillOpacity: 0.95 });
        e.target.bringToFront();
      },
      mouseout: (e) => e.target.setStyle(style(feature)),
      click: () => onDistrictClick && onDistrictClick(stateName, districtName),
    });

    const lines = row && describe ? describe(row) : [emptyLabel];
    layer.bindTooltip(
      `<div style="font-family:'Outfit',sans-serif;padding:4px 6px;min-width:150px;">
         <strong style="color:#0f172a;font-size:13px;display:block;">${escapeHtml(districtName)}</strong>
         <span style="color:#64748b;font-size:11px;display:block;margin-bottom:4px;">${escapeHtml(stateName)}</span>
         ${lines.map((line, i) => `<span style="color:${i === 0 && row ? getRiskColor(row.risk) : "#334155"};font-size:12px;font-weight:${i === 0 ? 700 : 500};display:block;">${escapeHtml(line)}</span>`).join("")}
       </div>`,
      { sticky: true, direction: "top" }
    );
  };

  // Leaflet builds the layer once: change the key whenever the data behind the styling changes
  const layerKey = useMemo(
    () => `${rows.length}:${rows.slice(0, 40).map(r => `${r.District}${r.risk}`).join("")}`,
    [rows]
  );

  return (
    <div className="relative z-0" style={{ height: "560px", width: "100%", background: "#f8fafc" }}>
      <MapContainer
        center={MAP.center}
        zoom={MAP.districtZoom}
        zoomSnap={0.1}
        style={{ height: "100%", width: "100%", background: "transparent" }}
        scrollWheelZoom={false}
        attributionControl={false}
      >
        <AttributionControl prefix={false} />
        {MAP.tileUrl && <TileLayer attribution={MAP.tileAttribution} url={MAP.tileUrl} />}
        {geoData?.features && (
          <GeoJSON key={layerKey} data={geoData} style={style} onEachFeature={onEachFeature} attribution={MAP.attribution} />
        )}
        {/* State outlines on top, for orientation */}
        {stateGeo?.features && <GeoJSON data={stateGeo} style={STATE_OUTLINE} interactive={false} />}
        {spreadVectors.length > 0 && <SpreadArrows vectors={spreadVectors} />}
      </MapContainer>
    </div>
  );
};

export default MapView;
