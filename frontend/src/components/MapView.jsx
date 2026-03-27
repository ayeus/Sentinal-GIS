import { MapContainer, TileLayer, GeoJSON, Marker, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import SpreadArrows from "./SpreadArrows";
import { Radio } from "lucide-react";
import { renderToStaticMarkup } from "react-dom/server";

const MapView = ({ predictions = [], geoData, viewMode = "current", spreadVectors = [], liveSignals = {}, onDistrictClick }) => {
  const normalize = (name) =>
    name?.toLowerCase().replace(/[^a-z]/g, "").trim();

  // Custom icon for Live Signals
  const liveIcon = L.divIcon({
    html: renderToStaticMarkup(
      <div className="relative flex items-center justify-center">
        <div className="absolute w-8 h-8 bg-red-500 rounded-full opacity-20 animate-ping"></div>
        <div className="relative p-1.5 bg-red-600 rounded-full text-white shadow-lg border-2 border-white">
          <Radio size={12} strokeWidth={3} />
        </div>
      </div>
    ),
    className: "custom-div-icon",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  const getColor = (risk, confidence = 1) => {
    if (!risk) return "#e5e7eb"; 
    const c = confidence;
    if (risk === "High") {
      if (c >= 0.9) return "#be123c"; // rose-700
      if (c >= 0.7) return "#e11d48"; // rose-600
      if (c >= 0.5) return "#f43f5e"; // rose-500
      return "#fb7185"; // rose-400
    }
    if (risk === "Medium") {
      if (c >= 0.9) return "#b45309"; // amber-700
      if (c >= 0.7) return "#d97706"; // amber-600
      if (c >= 0.5) return "#f59e0b"; // amber-500
      return "#fbbf24"; // amber-400
    }
    if (risk === "Low") {
      if (c >= 0.9) return "#047857"; // emerald-700
      if (c >= 0.7) return "#059669"; // emerald-600
      if (c >= 0.5) return "#10b981"; // emerald-500
      return "#34d399"; // emerald-400
    }
    return "#e5e7eb";
  };

  const getMatch = (feature) => {
    const dName = normalize(feature.properties.NAME_2);
    return predictions.find(p => normalize(p.District) === dName);
  };

  const getLabel = (feature) => {
    return feature.properties.NAME_2 || "Unknown District";
  };

  const style = (feature) => {
    const prediction = getMatch(feature);
    const hasSignal = liveSignals[feature.properties.NAME_1] || liveSignals[feature.properties.NAME_2];
    
    return {
      fillColor: getColor(prediction?.risk, prediction?.confidence),
      weight: hasSignal ? 3 : (prediction ? (viewMode === "current" ? 1 : 2) : 1),
      color: hasSignal ? "#ef4444" : (prediction ? "#ffffff" : "#cbd5e1"), 
      fillOpacity: prediction ? 0.8 : 0.5,
      dashArray: hasSignal ? (prediction ? "" : "3, 6") : ""
    };
  };

  const onEachFeature = (feature, layer) => {
    const prediction = getMatch(feature);
    const labelName = getLabel(feature);
    const hasSignal = liveSignals[feature.properties.NAME_1] || liveSignals[feature.properties.NAME_2];

    layer.on({
      mouseover: (e) => {
        const l = e.target;
        l.setStyle({ weight: 4, color: "#0f172a", fillOpacity: 0.9 });
        l.bringToFront();
      },
      mouseout: (e) => {
        const l = e.target;
        l.setStyle(style(feature));
      },
      click: () => {
        const stateName = feature.properties.NAME_1 || "";
        const districtName = feature.properties.NAME_2 || "";
        if (onDistrictClick && districtName) {
          onDistrictClick(stateName, districtName);
        }
      }
    });

    const signalTag = hasSignal ? `<span style="background: #ef4444; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 800; display:inline-block; margin-bottom: 4px; animation: pulse 2s infinite;">LIVE NEWS ALERT</span>` : "";

    if (prediction) {
      layer.bindPopup(
        `<div style="font-family: 'Outfit', sans-serif; padding: 4px; text-align: center;">
           ${signalTag}
           <strong style="color: #0f172a; font-size: 16px; display:block; margin-bottom: 4px;">${labelName}</strong>
           <span style="color: #1e293b; font-size: 14px; font-weight: 600; display:block;">Risk Level: <span style="color: ${getColor(prediction.risk, 1)}">${prediction.risk}</span></span>
         </div>`
      );
    } else {
      layer.bindPopup(
        `<div style="font-family: 'Outfit', sans-serif; padding: 4px; text-align: center;">
           ${signalTag}
           <strong style="color: #0f172a; font-size: 14px;">${labelName || "Unknown"}</strong><br/>
           <span style="color: #64748b; font-size: 12px;">${hasSignal ? "Emerging threat reported in news" : "No data available"}</span>
         </div>`
      );
    }
  };

  // Extract markers for signals
  const signalMarkers = [];
  if (geoData?.features) {
    geoData.features.forEach(feature => {
      const dName = feature.properties.NAME_2;
      const sName = feature.properties.NAME_1;
      if (liveSignals[dName] || liveSignals[sName]) {
        // Calculate a rough centroid from the first polygon's coordinates
        try {
          let coords = feature.geometry.coordinates;
          if (feature.geometry.type === "MultiPolygon") coords = coords[0][0];
          else coords = coords[0];
          
          const lat = coords[0][1];
          const lng = coords[0][0];
          
          signalMarkers.push({
            id: feature.properties.ID_2 || feature.properties.ID_1,
            position: [lat, lng],
            label: dName || sName
          });
        } catch (e) {}
      }
    });
  }

  return (
    <div style={{ height: "500px", width: "100%", background: "#f8fafc" }}>
      <MapContainer
        center={[22.9734, 78.6569]}
        zoom={4.7}
        style={{ height: "100%", width: "100%", background: "transparent" }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        {geoData?.features && (
          <GeoJSON
            key={JSON.stringify(predictions) + JSON.stringify(liveSignals) + (geoData ? "loaded" : "loading") + viewMode}
            data={geoData}
            style={style}
            onEachFeature={onEachFeature}
          />
        )}
        {signalMarkers.map(marker => (
          <Marker key={marker.id} position={marker.position} icon={liveIcon}>
            <Tooltip permanent direction="top" className="custom-tooltip">
              <span className="font-bold text-[9px] text-red-700 bg-white/90 px-1 rounded shadow-sm border border-red-100">
                LIVE: {marker.label}
              </span>
            </Tooltip>
          </Marker>
        ))}
        {spreadVectors.length > 0 && <SpreadArrows vectors={spreadVectors} />}
      </MapContainer>
    </div>
  );
};

export default MapView;