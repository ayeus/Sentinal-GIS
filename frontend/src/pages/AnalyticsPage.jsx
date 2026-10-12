import TrendChart from "../components/TrendChart";
import AnomalyPanel from "../components/AnomalyPanel";
import CoOccurrenceHeatmap from "../components/CoOccurrenceHeatmap";
import FilterBar from "../components/FilterBar";
import HowToRead from "../components/HowToRead";
import useSurveillanceFilters from "../hooks/useSurveillanceFilters";

const AnalyticsPage = () => {
  const filters = useSurveillanceFilters();
  const { disease, period } = filters;

  return (
    <div className="container mx-auto px-6 py-8 space-y-6">
      <div>
        <div className="flex flex-wrap items-center gap-4 mb-2">
          <h2 className="text-2xl font-bold text-gray-900 flex-1">Trends</h2>
          <FilterBar {...filters} />
        </div>
        <p className="text-sm text-gray-500">
          Descriptive statistics of outbreaks reported to IDSP. The trend covers the whole record; the other panels
          follow the selected period.
        </p>
      </div>

      <HowToRead points={[
        "The chart counts reported outbreaks month by month over the whole record. Switch between outbreaks, cases and deaths, and pick a disease at the top right.",
        "“Unusually high case counts” lists districts that reported far more cases than the average district in the chosen period.",
        "The grid shows which diseases tend to be reported from the same districts (1.0 = always together, 0 = unrelated).",
      ]} />

      <TrendChart disease={disease || null} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AnomalyPanel disease={disease || null} period={period} />
        <CoOccurrenceHeatmap period={period} />
      </div>
    </div>
  );
};

export default AnalyticsPage;
