import TrendChart from "../components/TrendChart";
import AnomalyPanel from "../components/AnomalyPanel";
import CoOccurrenceHeatmap from "../components/CoOccurrenceHeatmap";
import FilterBar from "../components/FilterBar";
import useSurveillanceFilters from "../hooks/useSurveillanceFilters";

const AnalyticsPage = () => {
  const filters = useSurveillanceFilters();
  const { disease, period } = filters;

  return (
    <div className="container mx-auto px-6 py-8 space-y-6">
      <div>
        <div className="flex flex-wrap items-center gap-4 mb-2">
          <h2 className="text-xl font-bold text-gray-900 flex-1">Analytics</h2>
          <FilterBar {...filters} />
        </div>
        <p className="text-sm text-gray-500">
          Descriptive statistics of outbreaks reported to IDSP. The trend covers the whole record; the other panels
          follow the selected period.
        </p>
      </div>

      <TrendChart disease={disease || null} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AnomalyPanel disease={disease || null} period={period} />
        <CoOccurrenceHeatmap period={period} />
      </div>
    </div>
  );
};

export default AnalyticsPage;
