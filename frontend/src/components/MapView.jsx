import { MapContainer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const getColor = (risk) => {
  if (risk === "High") return "#d73027";
  if (risk === "Medium") return "#fc8d59";
  if (risk === "Low") return "#1a9850";
  return "#cccccc";
};

const MapView = ({ geoData, riskData }) => {
  const style = (feature) => {
    const stateName = feature.properties.state;
    const match = riskData.find((r) => r.state === stateName);

    return {
      fillColor: match ? getColor(match.risk) : "#ccc",
      weight: 1,
      color: "#333",
      fillOpacity: 0.75
    };
  };

  return (
    <MapContainer
      style={{ height: "600px", width: "100%" }}
      center={[22.5, 78.9]}
      zoom={5}
    >
      <GeoJSON data={geoData} style={style} />
    </MapContainer>
  );
};

export default MapView;
