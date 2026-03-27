import { useState, useEffect } from "react";
import { getCoOccurrence } from "../services/api";
import { Grid3x3 } from "lucide-react";

const CoOccurrenceHeatmap = ({ year }) => {
  const [diseases, setDiseases] = useState([]);
  const [matrix, setMatrix] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getCoOccurrence(year)
      .then((res) => {
        setDiseases(res.diseases || []);
        setMatrix(res.matrix || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [year]);

  if (loading) {
    return <div className="glass-panel p-6 text-center text-gray-400 text-sm animate-pulse">Computing correlations…</div>;
  }

  if (!diseases.length) {
    return (
      <div className="glass-panel p-5 text-center text-gray-400 text-sm">
        Not enough disease variety for co-occurrence analysis.
      </div>
    );
  }

  const getCorr = (d1, d2) => {
    const item = matrix.find((m) => m.disease1 === d1 && m.disease2 === d2);
    return item ? item.correlation : 0;
  };

  const getColor = (val) => {
    if (val >= 0.7) return "bg-red-500 text-white";
    if (val >= 0.4) return "bg-orange-400 text-white";
    if (val >= 0.2) return "bg-amber-300 text-gray-800";
    if (val >= 0) return "bg-emerald-100 text-gray-700";
    if (val >= -0.3) return "bg-blue-100 text-gray-700";
    return "bg-blue-400 text-white";
  };

  // Truncate disease names for display
  const shortName = (n) => (n.length > 12 ? n.slice(0, 10) + "…" : n);

  return (
    <div className="glass-panel p-5">
      <h3 className="text-base font-bold text-gray-800 flex items-center gap-2 mb-4">
        <Grid3x3 className="w-4 h-4 text-purple-600" />
        Disease Co-occurrence Matrix
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]" style={{ borderCollapse: "separate", borderSpacing: "2px" }}>
          <thead>
            <tr>
              <th className="p-1"></th>
              {diseases.map((d) => (
                <th key={d} className="p-1 font-bold text-gray-600 text-center" style={{ writingMode: "vertical-lr", height: "80px" }}>
                  {shortName(d)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {diseases.map((d1) => (
              <tr key={d1}>
                <td className="p-1 font-bold text-gray-700 whitespace-nowrap text-right pr-2">{shortName(d1)}</td>
                {diseases.map((d2) => {
                  const val = getCorr(d1, d2);
                  return (
                    <td
                      key={d2}
                      className={`p-1 text-center rounded-sm font-bold ${getColor(val)}`}
                      title={`${d1} ↔ ${d2}: ${val}`}
                      style={{ width: "28px", height: "28px", minWidth: "28px" }}
                    >
                      {val.toFixed(1)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2 mt-3 text-[10px] font-medium text-gray-500">
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-red-500 rounded-sm inline-block"></span> High Corr (≥0.7)</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-300 rounded-sm inline-block"></span> Moderate</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-emerald-100 rounded-sm inline-block border border-gray-200"></span> Low</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-400 rounded-sm inline-block"></span> Negative</span>
      </div>
    </div>
  );
};

export default CoOccurrenceHeatmap;
