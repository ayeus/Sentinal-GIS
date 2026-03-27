import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";

const RISK_COLORS = {
  High: "#be123c",
  Medium: "#d97706",
  Low: "#059669",
};

/**
 * SpreadArrows renders animated arrow lines (polylines with arrowheads) on a Leaflet map
 * for each disease spread vector (origin -> destination district).
 */
const SpreadArrows = ({ vectors = [] }) => {
  const map = useMap();
  const layerGroupRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    // Clean up previous arrows
    if (layerGroupRef.current) {
      layerGroupRef.current.clearLayers();
    } else {
      layerGroupRef.current = L.layerGroup().addTo(map);
    }

    vectors.forEach((v) => {
      const color = RISK_COLORS[v.spread_risk] || "#64748b";
      const origin = [v.origin_lat, v.origin_lon];
      const dest = [v.dest_lat, v.dest_lon];

      // Draw the connecting line
      const line = L.polyline([origin, dest], {
        color,
        weight: v.spread_risk === "High" ? 2.5 : 1.5,
        opacity: 0.7,
        dashArray: v.spread_risk === "High" ? null : "4 4",
      });

      // Draw a circle at the origin (source of spread)
      const originMarker = L.circleMarker(origin, {
        radius: v.spread_risk === "High" ? 6 : 4,
        color,
        fillColor: color,
        fillOpacity: 0.9,
        weight: 1,
      });

      // Add arrowhead marker at destination  
      const arrowIcon = L.divIcon({
        html: `<div style="
          width: 0; height: 0;
          border-left: 5px solid transparent;
          border-right: 5px solid transparent;
          border-bottom: 10px solid ${color};
          transform: rotate(${bearing(origin, dest)}deg);
          opacity: 0.85;
        "></div>`,
        className: "",
        iconSize: [10, 10],
        iconAnchor: [5, 5],
      });

      const arrowMarker = L.marker(dest, { icon: arrowIcon });

      // Tooltip on hover
      const tooltip = `<div style="font-family: 'Outfit', sans-serif; font-size: 12px; padding: 6px 8px;">
        <strong>${v.origin_district}, ${v.origin_state}</strong>
        <span style="color:#64748b"> → </span>
        <strong>${v.dest_district}, ${v.dest_state}</strong><br/>
        <span style="color:${color}; font-weight:bold;">${v.spread_risk} Spread Risk</span>
        <span style="color:#94a3b8;"> | ${v.origin_cases} cases at source</span>
      </div>`;

      line.bindTooltip(tooltip, { sticky: true });
      originMarker.bindTooltip(tooltip, { sticky: true });

      layerGroupRef.current.addLayer(line);
      layerGroupRef.current.addLayer(originMarker);
      layerGroupRef.current.addLayer(arrowMarker);
    });

    return () => {
      if (layerGroupRef.current) {
        layerGroupRef.current.clearLayers();
      }
    };
  }, [map, vectors]);

  return null;
};

/** Calculate the bearing angle between two [lat, lon] points for the arrowhead rotation. */
function bearing([lat1, lon1], [lat2, lon2]) {
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const y = Math.sin(dLon);
  const x =
    Math.cos((lat1 * Math.PI) / 180) * Math.tan((lat2 * Math.PI) / 180) -
    Math.sin((lat1 * Math.PI) / 180) * Math.cos(dLon);
  const b = (Math.atan2(y, x) * 180) / Math.PI;
  return (b + 360) % 360;
}

export default SpreadArrows;
