import { useEffect, useState } from "react";
import { Database, FlaskConical, AlertTriangle, ExternalLink, Loader2 } from "lucide-react";
import useDataStatus from "../hooks/useDataStatus";
import { getModelCard } from "../services/api";
import StatCard from "../components/StatCard";
import { RISK_COLORS, formatDate, formatNumber, formatPercent } from "../config";

const SOURCE_LABELS = {
  portal: "the official IDSP / NCDC site",
  google_drive: "IDSP's Google Drive links",
  archive: "Internet Archive copies of the IDSP files",
  upload: "manual upload",
  unknown: "earlier downloads",
};

const Section = ({ icon: Icon, title, children }) => (
  <section className="glass-panel p-6">
    <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
      <Icon className="w-5 h-5 text-blue-600" /> {title}
    </h3>
    {children}
  </section>
);

const Th = ({ children, right }) => (
  <th className={`py-2 px-3 text-[11px] font-bold uppercase tracking-wide text-gray-500 ${right ? "text-right" : "text-left"}`}>{children}</th>
);
const Td = ({ children, right, bold }) => (
  <td className={`py-2 px-3 text-sm ${right ? "text-right tabular-nums" : ""} ${bold ? "font-bold text-gray-900" : "text-gray-700"}`}>{children}</td>
);

/** One row of week cells per year: filled where the bulletin for that week is in the system. */
const CoverageGrid = ({ weeks }) => {
  const byYear = {};
  weeks.forEach(label => {
    const [year, week] = [label.slice(0, 4), Number(label.slice(6))];
    (byYear[year] = byYear[year] || new Set()).add(week);
  });
  return (
    <div className="space-y-1.5 overflow-x-auto">
      {Object.keys(byYear).sort().map(year => (
        <div key={year} className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-600 w-10 shrink-0">{year}</span>
          <div className="flex gap-[2px]">
            {Array.from({ length: 53 }, (_, i) => i + 1).map(week => (
              <span key={week} title={`${year} week ${week}: ${byYear[year].has(week) ? "bulletin ingested" : "no bulletin"}`}
                className={`w-2.5 h-4 rounded-[2px] ${byYear[year].has(week) ? "bg-blue-500" : "bg-gray-200"}`} />
            ))}
          </div>
          <span className="text-[11px] text-gray-500 shrink-0">{byYear[year].size} weeks</span>
        </div>
      ))}
      <p className="text-[11px] text-gray-500 pt-1">
        <span className="inline-block w-2.5 h-3 rounded-[2px] bg-blue-500 align-middle mr-1" /> bulletin in the system
        <span className="inline-block w-2.5 h-3 rounded-[2px] bg-gray-200 align-middle ml-3 mr-1" /> missing
      </p>
    </div>
  );
};

// Plain-language account of the last automatic check for new bulletins
const portalCheckText = (check) => {
  if (!check) {
    return <strong className="text-amber-700">No automatic check has run on this server yet.</strong>;
  }
  const when = formatDate(check.checked_at);
  if (!check.ok) {
    return (
      <strong className="text-red-700">
        Last check {when} failed ({check.error}): neither the official site nor its Internet Archive copy could be
        read. New bulletins must be uploaded by hand until this is resolved.
      </strong>
    );
  }
  const failed = check.failed_count ? ` ${check.failed_count} listed bulletin(s) could not be fetched.` : "";
  if (check.index_source?.origin === "archive") {
    return (
      <strong className="text-amber-700">
        Last check {when}: the official site could not be reached from this server, so the Internet Archive copy of
        its index (captured {formatDate(check.index_source.captured)}) was used. It lists bulletins up to{" "}
        {check.newest_week_listed}; anything published later is not available here until the official site is reachable
        or the PDF is uploaded. {check.downloaded} new bulletin(s) downloaded.{failed}
      </strong>
    );
  }
  return (
    <strong className="text-emerald-700">
      Last check {when}: official site reached, newest bulletin listed is {check.newest_week_listed},{" "}
      {check.downloaded} new bulletin(s) downloaded.{failed}
    </strong>
  );
};

const AboutPage = () => {
  const { status } = useDataStatus();
  const [card, setCard] = useState(null);
  const [cardError, setCardError] = useState("");

  useEffect(() => {
    getModelCard().then(setCard).catch(err => setCardError(err.message));
  }, []);

  const evaluation = card?.evaluation;
  const matched = status?.district_match || {};
  const totalMatched = Object.values(matched).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="container mx-auto px-6 py-8 space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">About the data and the forecast</h2>
        <p className="text-sm text-gray-500 mt-1">
          Where every number in this application comes from, how complete it is, and how well the forecast performed
          when tested. Read this before acting on anything shown elsewhere.
        </p>
      </div>

      {/* ── DATA ─────────────────────────────────────────────────────────── */}
      <Section icon={Database} title="Surveillance data">
        {!status ? (
          <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
        ) : !status.available ? (
          <p className="text-sm text-gray-600">{status.message}</p>
        ) : (
          <div className="space-y-5">
            <p className="text-sm text-gray-700 leading-relaxed">
              Source: <a href={status.source_url} target="_blank" rel="noreferrer" className="text-blue-700 font-bold hover:underline inline-flex items-center gap-1">
                {status.source} <ExternalLink className="w-3 h-3" /></a>.
              Each weekly bulletin lists the disease outbreaks that States and UTs reported, with district, case and
              death counts. The system reads the published PDFs; it has no access to unpublished or line-list data.
              {status.bulletin_sources && Object.keys(status.bulletin_sources).length > 0 && (
                <> Bulletin files were obtained from: {Object.entries(status.bulletin_sources).map(([source, n]) =>
                  `${SOURCE_LABELS[source] || source} (${n})`).join(", ")}.</>
              )}
            </p>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard label="Outbreaks" value={formatNumber(status.outbreaks)} border="border-blue-400" />
              <StatCard label="Cases / deaths" value={`${formatNumber(status.total_cases)} / ${formatNumber(status.total_deaths)}`} border="border-amber-400" />
              <StatCard label="Districts / states" value={`${status.districts} / ${status.states}`} border="border-indigo-400" />
              <StatCard label="Latest bulletin" value={formatDate(status.latest_week_end)}
                hint={`${status.data_age_days} days ago`} border={status.is_stale ? "border-amber-400" : "border-emerald-400"}
                tone={status.is_stale ? "text-amber-700" : "text-emerald-700"} />
            </div>

            <div>
              <h4 className="text-sm font-bold text-gray-800 mb-2">
                Weekly coverage: {status.bulletins_ingested} of {status.weeks_in_span} weeks ({status.weeks_missing} missing)
              </h4>
              <CoverageGrid weeks={status.bulletin_weeks} />
              <p className="text-xs text-gray-600 leading-relaxed mt-3">
                {status.weeks_with_no_outbreaks_reported?.length > 0 &&
                  `${status.weeks_with_no_outbreaks_reported.length} of the covered weeks are bulletins stating that no outbreaks were reported (${status.weeks_with_no_outbreaks_reported.join(", ")}); they count as covered, with zero outbreaks. `}
                Missing weeks are bulletins that have not been downloaded or uploaded. They are treated as unknown
                everywhere: charts show gaps, and the forecaster neither learns from nor counts them as quiet weeks.
                {status.pdfs_on_disk > status.pdfs_with_records &&
                  ` ${status.pdfs_on_disk - status.pdfs_with_records} of ${status.pdfs_on_disk} bulletins read contained no outbreak rows.`}
                {status.missing_weeks?.length > 0 && status.missing_weeks.length <= 20 &&
                  ` Missing: ${status.missing_weeks.join(", ")}.`}
              </p>
            </div>

            <div>
              <h4 className="text-sm font-bold text-gray-800 mb-2">Automatic updates</h4>
              <p className="text-xs text-gray-600 leading-relaxed">
                The server checks the official list of weekly reports (on the NCDC website) every few hours for new bulletins, and any PDF added with “Add IDSP
                bulletin” is processed at once; either way the dataset is rebuilt and the forecast retrained.{" "}
{portalCheckText(status.last_portal_check)}
              </p>
            </div>

            <div>
              <h4 className="text-sm font-bold text-gray-800 mb-2">Placing outbreaks on the map</h4>
              <p className="text-xs text-gray-600 leading-relaxed">
                District names in the bulletins are matched to 2021 district boundaries (geoBoundaries, from the Local
                Government Directory). Of {formatNumber(totalMatched)} outbreaks:{" "}
                <strong>{formatPercent((matched.exact || 0) / totalMatched)}</strong> matched by name,{" "}
                <strong>{formatPercent(((matched.alias || 0) + (matched.fuzzy || 0)) / totalMatched)}</strong> through a
                known renaming or spelling variant, and{" "}
                <strong>{formatPercent((matched.parent || 0) / totalMatched, 1)}</strong> belong to districts created
                after 2021 and are shown on the district they were carved from.
                {Object.keys(status.unmatched_districts || {}).length > 0
                  ? ` ${Object.values(status.unmatched_districts).reduce((a, b) => a + b, 0)} outbreaks could not be placed and appear in lists but not on the map: ${Object.keys(status.unmatched_districts).join("; ")}.`
                  : " None were left unplaced."}
              </p>
            </div>
          </div>
        )}
      </Section>

      {/* ── MODEL ────────────────────────────────────────────────────────── */}
      <Section icon={FlaskConical} title="Forecast model and its test results">
        {cardError ? (
          <p className="text-sm text-red-600">{cardError}</p>
        ) : !card ? (
          <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
        ) : !card.available ? (
          <p className="text-sm text-gray-600">{card.message}</p>
        ) : (
          <div className="space-y-6">
            <div className="text-sm text-gray-700 leading-relaxed space-y-2">
              <p>
                <strong>What it predicts.</strong> For each of {card.districts} districts and {card.diseases_modelled.length} diseases:
                the probability that IDSP reports at least one outbreak in the next {card.horizon_weeks} weeks. It does
                not predict case numbers. Diseases with too few reports to learn from are not forecast.
              </p>
              <p>
                <strong>How.</strong> {card.model}, trained on {formatNumber(card.training.rows)} district-disease-weeks
                ({card.training.first_week} to {card.training.last_week}), of which {formatPercent(card.training.base_rate, 1)} were
                followed by an outbreak. It uses only what was known at the time of each forecast: the district's own
                history, neighbouring districts, the rest of the state, and the season.
              </p>
              <p>
                <strong>How it was tested.</strong> {evaluation.method} The test period was {evaluation.holdout_first_week} to{" "}
                {evaluation.holdout_last_week}: {formatNumber(evaluation.holdout_rows)} forecasts,{" "}
                {formatNumber(evaluation.holdout_outbreak_periods)} of them followed by an outbreak
                ({formatPercent(evaluation.holdout_base_rate, 1)}).
              </p>
            </div>

            <div>
              <h4 className="text-sm font-bold text-gray-800 mb-2">What each risk tier meant in the test period</h4>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead><tr className="border-b border-gray-200">
                    <Th>Tier</Th><Th right>Forecast probability</Th><Th right>Share of all forecasts</Th>
                    <Th right>Outbreak actually followed</Th><Th right>Share of all outbreaks</Th>
                  </tr></thead>
                  <tbody>
                    {evaluation.tiers.map(t => (
                      <tr key={t.tier} className="border-b border-gray-100">
                        <Td bold><span className="inline-block w-3 h-3 rounded-sm mr-2 align-middle" style={{ backgroundColor: RISK_COLORS[t.tier] }} />{t.tier}</Td>
                        <Td right>{t.tier === "Minimal" ? "below " + formatPercent(evaluation.tiers[evaluation.tiers.length - 2].min_probability) : formatPercent(t.min_probability) + " or more"}</Td>
                        <Td right>{formatPercent(t.share_of_forecasts, 1)}</Td>
                        <Td right bold>{formatPercent(t.observed_outbreak_rate, 1)}</Td>
                        <Td right>{formatPercent(t.share_of_outbreaks_captured)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed mt-2">
                Read it this way: a High flag was followed by a reported outbreak about{" "}
                {formatPercent(evaluation.tiers[0].observed_outbreak_rate)} of the time, far above the{" "}
                {formatPercent(evaluation.holdout_base_rate, 1)} average, yet most High flags were not. And{" "}
                {formatPercent(evaluation.tiers[evaluation.tiers.length - 1].share_of_outbreaks_captured)} of outbreaks
                happened in district-disease pairs rated Minimal. The forecast helps decide where to look first; it
                cannot rule a district out.
              </p>
            </div>

            <div>
              <h4 className="text-sm font-bold text-gray-800 mb-2">Compared with simple rules</h4>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead><tr className="border-b border-gray-200">
                    <Th>Method</Th><Th right>Average precision</Th><Th right>ROC-AUC</Th>
                    <Th right>Hit rate in top 1%</Th><Th right>Outbreaks found in top 1%</Th>
                  </tr></thead>
                  <tbody>
                    <tr className="border-b border-gray-100 bg-blue-50/50">
                      <Td bold>SentinelGIS model</Td>
                      <Td right bold>{evaluation.model.average_precision.toFixed(3)}</Td>
                      <Td right bold>{evaluation.model.roc_auc.toFixed(3)}</Td>
                      <Td right bold>{formatPercent(evaluation.model.precision_top_1pct, 1)}</Td>
                      <Td right bold>{formatPercent(evaluation.model.recall_top_1pct, 1)}</Td>
                    </tr>
                    {evaluation.baselines.map(b => (
                      <tr key={b.name} className="border-b border-gray-100">
                        <Td>{b.name}</Td>
                        <Td right>{b.average_precision.toFixed(3)}</Td>
                        <Td right>{b.roc_auc.toFixed(3)}</Td>
                        <Td right>{formatPercent(b.precision_top_1pct, 1)}</Td>
                        <Td right>{formatPercent(b.recall_top_1pct, 1)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed mt-2">
                Average precision summarises how well the highest-ranked forecasts pick out real outbreaks (random
                guessing would score {evaluation.holdout_base_rate.toFixed(3)}). The model scores{" "}
                {evaluation.lift_over_best_baseline}× the best simple rule: a real but moderate improvement.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-bold text-gray-800 mb-2">By disease (test period)</h4>
                <table className="w-full border-collapse">
                  <thead><tr className="border-b border-gray-200">
                    <Th>Disease</Th><Th right>Outbreak periods</Th><Th right>Avg. precision</Th><Th right>ROC-AUC</Th>
                  </tr></thead>
                  <tbody>
                    {[...evaluation.per_disease].sort((a, b) => (b.average_precision || 0) - (a.average_precision || 0)).map(d => (
                      <tr key={d.disease} className="border-b border-gray-100">
                        <Td>{d.disease}</Td>
                        <Td right>{d.outbreak_periods}</Td>
                        <Td right bold>{d.average_precision !== undefined ? d.average_precision.toFixed(3) : "–"}</Td>
                        <Td right>{d.roc_auc !== undefined ? d.roc_auc.toFixed(3) : "–"}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="text-xs text-gray-600 leading-relaxed mt-2">
                  Forecasts for diseases near the bottom of this table are weak and should carry little weight.
                </p>
              </div>
              <div>
                <h4 className="text-sm font-bold text-gray-800 mb-2">What the model relies on</h4>
                <div className="space-y-2">
                  {card.drivers.filter(d => d.share >= 0.005).map(d => (
                    <div key={d.factor}>
                      <div className="flex justify-between text-xs text-gray-700 mb-0.5">
                        <span>{d.factor}</span><span className="font-bold tabular-nums">{formatPercent(d.share)}</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full" style={{ width: `${d.share * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-600 leading-relaxed mt-2">
                  Share of the model's test accuracy lost when each kind of information is scrambled.
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
              <h4 className="text-sm font-bold text-amber-900 flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4" /> Limitations
              </h4>
              <ul className="list-disc pl-5 space-y-1 text-xs text-amber-900 leading-relaxed">
                {card.limitations.map(l => <li key={l}>{l}</li>)}
              </ul>
            </div>

            <p className="text-[11px] text-gray-400">
              Model trained {formatDate(card.trained_at)} · forecast window {formatDate(card.forecast.window_start)} to{" "}
              {formatDate(card.forecast.window_end)} · retrained automatically whenever a new bulletin is ingested.
            </p>
          </div>
        )}
      </Section>
    </div>
  );
};

export default AboutPage;
