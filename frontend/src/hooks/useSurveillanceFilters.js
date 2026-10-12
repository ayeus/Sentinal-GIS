import { useState, useEffect, useMemo } from "react";
import { getDiseases, getAvailableYears } from "../services/api";
import { DEFAULT_DISEASE } from "../config";

/**
 * Disease + period filter state shared by the Surveillance and Analytics
 * pages. Options come from the dataset. The period defaults to the latest
 * reporting weeks, so the first thing shown is the most recent picture.
 *
 * `periodKey` is "w12" (latest 12 reporting weeks) or "y2025" (calendar year);
 * `period` is the matching API parameter object, null until options have loaded.
 */
const useSurveillanceFilters = () => {
  const [disease, setDisease] = useState(DEFAULT_DISEASE);
  const [periodKey, setPeriodKey] = useState(null);
  const [diseasesList, setDiseasesList] = useState([]);
  const [modelledDiseases, setModelledDiseases] = useState([]);
  const [yearsList, setYearsList] = useState([]);

  useEffect(() => {
    getDiseases().then(res => {
      const diseases = res.diseases || [];
      setDiseasesList(diseases);
      setModelledDiseases(res.modelled || []);
      // Fall back to "All Diseases" if the configured default is not in the data
      setDisease(current => (current && !diseases.includes(current) ? "" : current));
    }).catch(console.error);
    getAvailableYears().then(res => {
      setYearsList(res.years || []);
      setPeriodKey(`w${res.recent_weeks_default || 12}`);
    }).catch(console.error);
  }, []);

  const period = useMemo(() => {
    if (!periodKey) return null;
    const value = Number(periodKey.slice(1));
    return periodKey.startsWith("w") ? { weeks: value } : { year: value };
  }, [periodKey]);

  return { disease, setDisease, periodKey, setPeriodKey, period, diseasesList, modelledDiseases, yearsList };
};

export default useSurveillanceFilters;
