import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

import MapView from "../components/MapView";
import RiskCard from "../components/RiskCard";
import Legend from "../components/Legend";
import StatCard from "../components/StatCard";
import DistrictDetailPanel from "../components/DistrictDetailPanel";
import FilterBar from "../components/FilterBar";
import useSurveillanceFilters from "../hooks/useSurveillanceFilters";
import useDataStatus from "../hooks/useDataStatus";
import { getCurrentStatus, getDistrictGeoJSON } from "../services/api";
import { formatDate, formatNumber } from "../config";

const describe = (row) => [
  `${formatNumber(row.Cases)} cases reported`,
  `${row.Outbreaks} outbreak${row.Outbreaks === 1 ? "" : "s"} · ${formatNumber(row.Deaths)} deaths`,
  row.Diseases,
  `Latest report: week of ${formatDate(row.LatestWeek)}`,
];

const SurveillancePage = () => {
  const filters = useSurveillanceFilters();
  const { disease, period } = filters;
  const { status } = useDataStatus();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [districtGeoData, setDistrictGeoData] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);

  useEffect(() => {
    getDistrictGeoJSON().then(setDistrictGeoData).catch(console.error);
  }, []);

  useEffect(() => {
    if (!period) return;
    // Ignore responses that arrive after the filters changed again
    let cancelled = false;
    setLoading(true);
    setErrorMsg("");
    getCurrentStatus(disease, period)
      .then(res => {
        if (cancelled) return;
        setData(res);
        if (!res.region_data?.length) setErrorMsg("No outbreaks were reported for these filters.");
      })
      .catch(err => {
        if (cancelled) return;
        setData(null);
        setErrorMsg(err.message);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [period, disease]);

  const rows = data?.region_data || [];
  const bands = status?.burden_bands;

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="flex flex-wrap items-center gap-4 mb-2">
        <h2 className="text-xl font-bold text-gray-900 flex-1">Reported outbreaks by district</h2>
        <FilterBar {...filters} />
      </div>
      <p className="text-sm text-gray-500 mb-6">
        What States and UTs reported to IDSP
        {data?.period?.from ? <> between <strong>{formatDate(data.period.from)}</strong> and <strong>{formatDate(data.period.to)}</strong></> : null}.
        These are recorded facts, not predictions.
      </p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Outbreaks reported" value={formatNumber(data?.total_outbreaks)} border="border-blue-400" tone="text-blue-700" />
        <StatCard label="Districts affected" value={formatNumber(rows.length)} border="border-indigo-400" tone="text-indigo-700" />
        <StatCard label="Cases" value={formatNumber(data?.total_cases)} border="border-amber-400" tone="text-amber-700" />
        <StatCard label="Deaths" value={formatNumber(data?.total_deaths)} border="border-rose-400" tone="text-rose-700" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 flex flex-col gap-4">
          <div className="glass-panel overflow-hidden p-1 shadow-sm">
            <MapView rows={rows} geoData={districtGeoData} describe={describe}
              emptyLabel="No outbreak reported in this period"
              onDistrictClick={(state, district) => setSelectedDistrict({ state, district })} />
          </div>
          <Legend
            title="Cases reported"
            emptyLabel="None reported"
            items={[
              { risk: "High", label: bands ? `More than ${bands.high_above_cases}` : "High" },
              { risk: "Medium", label: bands ? `${bands.medium_above_cases + 1} to ${bands.high_above_cases}` : "Medium" },
              { risk: "Low", label: bands ? `1 to ${bands.medium_above_cases}` : "Low" },
            ]}
            note="Colour shows the total number of cases reported for the district in the selected period. A district without colour had no outbreak reported, which is not proof that none occurred."
          />
        </div>

        <div className="lg:col-span-4">
          <h3 className="text-lg font-bold text-gray-900 mb-3 border-b border-gray-200 pb-2">
            Districts <span className="text-xs font-medium text-gray-400 ml-1">{rows.length} · most cases first</span>
          </h3>
          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>
          ) : errorMsg ? (
            <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg border border-gray-200">{errorMsg}</p>
          ) : (
            <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-2 custom-scrollbar">
              {rows.map(row => (
                <RiskCard key={`${row.State}|${row.District}`}
                  title={row.District} subtitle={row.State} risk={row.risk}
                  caption={row.Diseases}
                  value={formatNumber(row.Cases)} valueLabel="cases"
                  facts={[
                    `${row.Outbreaks} outbreak${row.Outbreaks === 1 ? "" : "s"}`,
                    `${formatNumber(row.Deaths)} deaths`,
                    `latest: week of ${formatDate(row.LatestWeek)}`,
                  ]}
                  onClick={() => setSelectedDistrict({ state: row.State, district: row.District })} />
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedDistrict && (
        <DistrictDetailPanel state={selectedDistrict.state} district={selectedDistrict.district}
          onClose={() => setSelectedDistrict(null)} />
      )}
    </div>
  );
};

export default SurveillancePage;
