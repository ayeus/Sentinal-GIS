import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

import MapView from "../components/MapView";
import RiskCard from "../components/RiskCard";
import Legend from "../components/Legend";
import StatCard from "../components/StatCard";
import FilterBar from "../components/FilterBar";
import HowToRead from "../components/HowToRead";
import ListTools, { downloadCsv, filterRows } from "../components/ListTools";
import useDistrictPanel from "../hooks/useDistrictPanel";
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
  const [listFilter, setListFilter] = useState({ text: "", state: "" });
  const { openDistrict } = useDistrictPanel();

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
  const shownRows = filterRows(rows, listFilter);
  const bands = status?.burden_bands;
  const top = rows[0];

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="flex flex-wrap items-center gap-4 mb-2">
        <h2 className="text-2xl font-bold text-gray-900 flex-1">Reported outbreaks</h2>
        <FilterBar {...filters} />
      </div>
      <p className="text-sm text-gray-600 mb-4 max-w-4xl leading-relaxed">
        {data?.period?.from ? (
          <>
            Between <strong>{formatDate(data.period.from)}</strong> and <strong>{formatDate(data.period.to)}</strong>,{" "}
            <strong>{formatNumber(data.total_outbreaks)} outbreak{data.total_outbreaks === 1 ? " was" : "s were"}</strong> reported
            to IDSP from <strong>{formatNumber(rows.length)} district{rows.length === 1 ? "" : "s"}</strong>
            {top ? <>. Most cases: <strong>{top.District}, {top.State}</strong> ({formatNumber(top.Cases)})</> : null}.
          </>
        ) : "What States and UTs reported to IDSP."}{" "}
        These are recorded facts, not predictions.
      </p>

      <HowToRead points={[
        "Each coloured district reported at least one outbreak in the period chosen at the top right. The colour shows how many cases were reported there.",
        "Hover over a district to see its numbers. Click it, or a card in the list, to open its full record.",
        "Use “Find a district” at the top of the page to jump straight to any district.",
        "A grey district means nothing was reported from it. That is not proof that nothing happened.",
      ]} />

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
              onDistrictClick={openDistrict} />
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
            Districts <span className="text-xs font-medium text-gray-400 ml-1">{shownRows.length} of {rows.length} · most cases first</span>
          </h3>
          {rows.length > 0 && (
            <ListTools rows={rows} filter={listFilter} setFilter={setListFilter}
              onDownload={() => downloadCsv("reported-outbreaks.csv", [
                ["State", "State"], ["District", "District"], ["Outbreaks", "Outbreaks"], ["Cases", "Cases"],
                ["Deaths", "Deaths"], ["Diseases", "Diseases"], ["Latest report week", "LatestWeek"],
              ], shownRows)} />
          )}
          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>
          ) : errorMsg ? (
            <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg border border-gray-200">{errorMsg}</p>
          ) : (
            <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-2 custom-scrollbar">
              {shownRows.length === 0 && <p className="text-sm text-gray-500 p-3">No district in the list matches.</p>}
              {shownRows.map(row => (
                <RiskCard key={`${row.State}|${row.District}`}
                  title={row.District} subtitle={row.State} risk={row.risk}
                  caption={row.Diseases}
                  value={formatNumber(row.Cases)} valueLabel="cases"
                  facts={[
                    `${row.Outbreaks} outbreak${row.Outbreaks === 1 ? "" : "s"}`,
                    `${formatNumber(row.Deaths)} deaths`,
                    `latest: week of ${formatDate(row.LatestWeek)}`,
                  ]}
                  onClick={() => openDistrict(row.State, row.District)} />
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
};

export default SurveillancePage;
