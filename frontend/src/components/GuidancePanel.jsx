import { useEffect, useState } from "react";
import { BookOpen, ExternalLink } from "lucide-react";
import { getGuidance } from "../services/api";

const SECTIONS = [
  { key: "transmission", label: "How it spreads", style: "bg-amber-50/60 border-amber-100 text-amber-800" },
  { key: "prevention", label: "Prevention", style: "bg-emerald-50/60 border-emerald-100 text-emerald-800" },
  { key: "response", label: "Public-health response", style: "bg-blue-50/60 border-blue-100 text-blue-800" },
];

/**
 * Curated public-health guidance for a disease, shown with its source.
 * The text is a fixed summary of the cited fact sheet: it is not generated
 * and not tailored to any district.
 */
const GuidancePanel = ({ disease, compact = false }) => {
  const [guidance, setGuidance] = useState(null);

  useEffect(() => {
    if (!disease) { setGuidance(null); return; }
    let cancelled = false;
    setGuidance(null);
    getGuidance(disease)
      .then(res => { if (!cancelled) setGuidance(res); })
      .catch(err => { console.error(err); if (!cancelled) setGuidance({ available: false, error: true }); });
    return () => { cancelled = true; };
  }, [disease]);

  if (!disease || !guidance) return null;

  if (!guidance.available) {
    return (
      <p className="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg p-3 leading-relaxed">
        {guidance.error
          ? "Guidance could not be loaded."
          : `No curated guidance is available for ${disease}. Refer to NCDC / IDSP and State Health Department protocols.`}
      </p>
    );
  }

  return (
    <div className="space-y-2.5">
      {!compact && (
        <h4 className="text-sm font-bold text-gray-800 flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-blue-600" /> {guidance.disease}: public-health guidance
        </h4>
      )}
      {SECTIONS.map(({ key, label, style }) => (
        <div key={key} className={`border rounded-xl p-3 ${style}`}>
          <div className="text-[10px] font-bold uppercase tracking-wide mb-1">{label}</div>
          <p className="text-xs text-gray-700 leading-relaxed font-medium">{guidance[key]}</p>
        </div>
      ))}
      <a href={guidance.source_url} target="_blank" rel="noreferrer"
        className="text-xs font-bold text-blue-700 inline-flex items-center gap-1 hover:underline">
        Source: {guidance.source_name} <ExternalLink className="w-3 h-3" />
      </a>
      <p className="text-[10px] text-gray-400 leading-relaxed">{guidance.disclaimer}</p>
    </div>
  );
};

export default GuidancePanel;
