import { Download, Search } from "lucide-react";

const csvCell = (value) => {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

/** Save rows as a CSV file. `columns` is [[header, key], ...]. */
export const downloadCsv = (filename, columns, rows) => {
  const lines = [columns.map(([header]) => csvCell(header)).join(",")]
    .concat(rows.map(row => columns.map(([, key]) => csvCell(row[key])).join(",")));
  const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

/** Narrow a list by state and by typed text; returns rows matching both. */
export const filterRows = (rows, { text, state }) => {
  const q = text.trim().toLowerCase();
  return rows.filter(row =>
    (!state || row.State === state) &&
    (!q || `${row.District} ${row.State} ${row.Disease || row.Diseases || ""}`.toLowerCase().includes(q)));
};

/** Filter box + state picker + CSV button shown above a district list. */
const ListTools = ({ rows, filter, setFilter, onDownload }) => {
  const states = [...new Set(rows.map(r => r.State))].sort();
  return (
    <div className="flex gap-2 mb-3">
      <div className="relative flex-1 min-w-0">
        <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input type="search" value={filter.text} onChange={e => setFilter({ ...filter, text: e.target.value })}
          placeholder="Filter this list…" aria-label="Filter this list"
          className="w-full pl-8 pr-2 py-2 bg-white border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500/50 focus:outline-none" />
      </div>
      <select value={filter.state} onChange={e => setFilter({ ...filter, state: e.target.value })} aria-label="State"
        className="bg-white border border-gray-300 rounded-lg px-2 py-2 text-xs max-w-[9rem] focus:ring-2 focus:ring-blue-500/50 focus:outline-none">
        <option value="">All states</option>
        {states.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      {onDownload && (
        <button type="button" onClick={onDownload} title="Download this list as a spreadsheet (CSV)"
          className="shrink-0 px-2.5 py-2 bg-white border border-gray-300 rounded-lg text-xs font-bold text-gray-700 hover:bg-gray-50 flex items-center gap-1.5">
          <Download className="w-3.5 h-3.5" /> CSV
        </button>
      )}
    </div>
  );
};

export default ListTools;
