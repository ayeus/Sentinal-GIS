import { HelpCircle } from "lucide-react";

/** Collapsible plain-language guide to a page. `points` is a list of short sentences. */
const HowToRead = ({ points }) => (
  <details className="glass-panel px-4 py-3 mb-6 group">
    <summary className="cursor-pointer list-none flex items-center gap-2 text-sm font-bold text-blue-700 select-none">
      <HelpCircle className="w-4 h-4" />
      How to read this page
      <span className="text-xs font-medium text-gray-400 group-open:hidden">(show)</span>
      <span className="text-xs font-medium text-gray-400 hidden group-open:inline">(hide)</span>
    </summary>
    <ul className="list-disc pl-6 mt-3 space-y-1.5 text-sm text-gray-700 leading-relaxed">
      {points.map((point, i) => <li key={i}>{point}</li>)}
    </ul>
  </details>
);

export default HowToRead;
