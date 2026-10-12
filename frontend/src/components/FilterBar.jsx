import { RECENT_WEEK_OPTIONS } from "../config";

const SELECT_CLASS =
  "bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-sm font-medium focus:ring-2 focus:ring-blue-500/50 focus:outline-none max-w-[16rem]";

/** Disease + period dropdowns driven by useSurveillanceFilters. */
const FilterBar = ({ disease, setDisease, periodKey, setPeriodKey, diseasesList, yearsList, showPeriod = true }) => (
  <>
    {diseasesList.length > 0 && (
      <select value={disease} onChange={e => setDisease(e.target.value)} className={SELECT_CLASS} aria-label="Disease">
        <option value="">All Diseases</option>
        {diseasesList.map(d => <option key={d} value={d}>{d}</option>)}
      </select>
    )}
    {showPeriod && periodKey && (
      <select value={periodKey} onChange={e => setPeriodKey(e.target.value)} className={SELECT_CLASS} aria-label="Period">
        <optgroup label="Latest reports">
          {[...new Set([...RECENT_WEEK_OPTIONS, Number(periodKey.startsWith("w") ? periodKey.slice(1) : RECENT_WEEK_OPTIONS[0])])]
            .sort((a, b) => a - b)
            .map(w => <option key={w} value={`w${w}`}>Latest {w} weeks</option>)}
        </optgroup>
        <optgroup label="Calendar year">
          {[...yearsList].reverse().map(y => <option key={y} value={`y${y}`}>{y}</option>)}
        </optgroup>
      </select>
    )}
  </>
);

export default FilterBar;
