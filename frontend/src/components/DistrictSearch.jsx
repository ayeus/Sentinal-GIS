import { useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";
import { getDistrictGeoJSON } from "../services/api";
import useDistrictPanel from "../hooks/useDistrictPanel";
import { GEO_STATE_KEY, GEO_DISTRICT_KEY } from "../config";

const MAX_RESULTS = 8;

/** Type a district or state name, pick a result, and its record opens. */
const DistrictSearch = () => {
  const { openDistrict } = useDistrictPanel();
  const [places, setPlaces] = useState([]);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef(null);

  useEffect(() => {
    getDistrictGeoJSON()
      .then(geo => setPlaces(
        geo.features
          .map(f => ({ state: f.properties[GEO_STATE_KEY], district: f.properties[GEO_DISTRICT_KEY] }))
          .filter(p => p.state && p.district)
          .sort((a, b) => a.district.localeCompare(b.district))
      ))
      .catch(console.error);
  }, []);

  useEffect(() => {
    const close = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    // Districts whose name starts with the text first, then any district or state containing it
    const starts = places.filter(p => p.district.toLowerCase().startsWith(q));
    const contains = places.filter(p => !p.district.toLowerCase().startsWith(q)
      && (p.district.toLowerCase().includes(q) || p.state.toLowerCase().includes(q)));
    return [...starts, ...contains].slice(0, MAX_RESULTS);
  }, [query, places]);

  const choose = (place) => {
    openDistrict(place.state, place.district);
    setQuery("");
    setOpen(false);
  };

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(i => Math.min(i + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(i => Math.max(i - 1, 0)); }
    else if (e.key === "Enter" && results[active]) choose(results[active]);
    else if (e.key === "Escape") setOpen(false);
  };

  return (
    <div ref={boxRef} className="relative w-full sm:w-64">
      <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
      <input
        type="search"
        value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true); setActive(0); }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder="Find a district…"
        aria-label="Find a district"
        className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-300 rounded-xl text-sm focus:bg-white focus:ring-2 focus:ring-blue-500/50 focus:outline-none"
      />
      {open && query.trim().length >= 2 && (
        <ul className="absolute z-40 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
          {results.length === 0 ? (
            <li className="px-3 py-2.5 text-sm text-gray-500">No district matches “{query.trim()}”.</li>
          ) : results.map((place, i) => (
            <li key={`${place.state}|${place.district}`}>
              <button type="button" onMouseEnter={() => setActive(i)} onClick={() => choose(place)}
                className={`w-full text-left px-3 py-2 text-sm ${i === active ? "bg-blue-50" : "bg-white"}`}>
                <span className="font-bold text-gray-900">{place.district}</span>
                <span className="text-gray-500"> · {place.state}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default DistrictSearch;
