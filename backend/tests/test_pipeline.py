"""
Fast checks of the parts where a silent mistake would put wrong numbers on
screen: PDF row parsing, cleaning, name resolution, and the guarantee that
forecast features never see the future.

    cd backend && python -m unittest discover -s tests -v
"""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from app.services import gazetteer
from app.services.forecasting import Panel
from data import clean_data, pdf_extractor


class ExtractorTests(unittest.TestCase):
    def test_row_with_reporting_date(self):
        row = ["AP/GUN/2025/45/1997", "Andhra Pradesh", "Guntur", "Acute Diarrhoeal\nDisease", "457", "0",
               "04-11- 2025", "04-11- 2025", "Under Control", "Cases of vomiting and loose stools"]
        record = pdf_extractor._parse_row(row)
        self.assertEqual(record["outbreak_id"], "AP/GUN/2025/45/1997")
        self.assertEqual(record["district"], "Guntur")
        self.assertEqual(record["disease"], "Acute Diarrhoeal Disease")
        self.assertEqual((record["cases"], record["deaths"]), ("457", "0"))
        self.assertEqual(record["status"], "Under Control")
        self.assertTrue(record["comments"].startswith("Cases of vomiting"))

    def test_late_reported_row_has_no_reporting_date(self):
        row = ["MP/BTU/2022/20/300", "Madhya Pradesh", "Betul", "Food Poisoning", "65", "00",
               "06-05-22", "Completed", "Cases reported from Village Pindrai"]
        record = pdf_extractor._parse_row(row)
        self.assertEqual(record["start_date"], "06-05-22")
        self.assertEqual(record["report_date"], "")
        self.assertEqual(record["status"], "Completed")

    def test_non_outbreak_rows_are_ignored(self):
        self.assertIsNone(pdf_extractor._parse_row(["Unique ID.", "Name of State/UT", "Name of District"]))
        self.assertIsNone(pdf_extractor._parse_row(["No. of States/UT's Submitted outbreak report", None, "31"]))

    def test_week_range_on_cover(self):
        start, end = pdf_extractor._parse_week_range("28th Week (7th July 2025 to 13th July 2025)")
        self.assertEqual((start, end), (date(2025, 7, 7), date(2025, 7, 13)))
        start, end = pdf_extractor._parse_week_range("29th December to 4th January 2026")
        self.assertEqual((start, end), (date(2025, 12, 29), date(2026, 1, 4)))


class CleaningTests(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(clean_data.parse_date("04-11- 2025"), date(2025, 11, 4))
        self.assertEqual(clean_data.parse_date("06-05-22"), date(2022, 5, 6))
        self.assertIsNone(clean_data.parse_date("???"))
        self.assertIsNone(clean_data.parse_date("31-02-2024"))

    def test_disease_names(self):
        self.assertEqual(clean_data.clean_disease("Acute Gastroenteri Tis"), "Acute Diarrheal Disease")
        self.assertEqual(clean_data.clean_disease("Suspected Food Poisoning"), "Food Poisoning")
        self.assertEqual(clean_data.clean_disease("Hepatitis A & E"), "Hepatitis / Jaundice")
        self.assertEqual(clean_data.clean_disease("Animal Bite - Dog Bite"), "Animal Bite")
        self.assertEqual(clean_data.clean_disease("Human Rabies"), "Rabies")
        self.assertEqual(clean_data.clean_disease("Fever"), "Fever of Unknown Origin")

    def test_counts(self):
        self.assertEqual(clean_data.clean_cases("03 birds"), 3)
        self.assertEqual(clean_data.clean_cases(""), 0)

    def test_follow_up_keeps_latest_figures_and_bad_dates_fall_back(self):
        base = {"state": "Kerala", "district": "Kollam", "disease": "Dengue", "deaths": "0",
                "report_date": "", "status": "Under Control", "comments": "", "week_start": "", "week_end": ""}
        raw = pd.DataFrame([
            {**base, "outbreak_id": "KL/KOA/2023/04/074", "cases": "23", "start_date": "27-01-2023",
             "bulletin_year": "2023", "bulletin_week": "4", "source_file": "a.pdf"},
            {**base, "outbreak_id": "KL/KOA/2023/04/074", "cases": "41", "start_date": "27-01-2023",
             "bulletin_year": "2023", "bulletin_week": "6", "source_file": "b.pdf"},
            {**base, "outbreak_id": "KL/KOA/2023/05/090", "cases": "5", "start_date": "27-01-2032",
             "bulletin_year": "2023", "bulletin_week": "5", "source_file": "c.pdf"},
        ])
        clean, quality = clean_data.build_clean_frame(raw)
        self.assertEqual(len(clean), 2)
        self.assertEqual(quality["follow_up_rows_merged"], 1)
        first = clean[clean["OutbreakID"] == "KL/KOA/2023/04/074"].iloc[0]
        self.assertEqual(first["Cases"], 41)
        self.assertEqual(first["Date"], "2023-01-27")
        # A start date in the future is impossible: fall back to the reporting week
        second = clean[clean["OutbreakID"] == "KL/KOA/2023/05/090"].iloc[0]
        self.assertEqual((second["Date"], second["DateSource"]), ("2023-01-30", "week_start"))


class GazetteerTests(unittest.TestCase):
    def test_states(self):
        self.assertEqual(gazetteer.resolve_state("Maharashtr a"), "Maharashtra")
        self.assertEqual(gazetteer.resolve_state("Jharkhand (IHIP)"), "Jharkhand")
        self.assertEqual(gazetteer.resolve_state("Jammu & Kashmir"), "Jammu and Kashmir")
        self.assertEqual(gazetteer.resolve_state("D&N Haveli"), "Dadra and Nagar Haveli and Daman and Diu")
        self.assertIsNone(gazetteer.resolve_state("Name of State/UT"))

    def test_districts(self):
        self.assertEqual(gazetteer.resolve_district("Kerala", "Thiruvanan thapuram"), ("Thiruvananthapuram", "exact"))
        self.assertEqual(gazetteer.resolve_district("Karnataka", "Kalaburagi"), ("Gulbarga", "alias"))
        self.assertEqual(gazetteer.resolve_district("Kerala", "Cannanore (Kannur)"), ("Kannur", "exact"))
        self.assertEqual(gazetteer.resolve_district("Andhra Pradesh", "Palnadu"), ("Guntur", "parent"))
        self.assertEqual(gazetteer.resolve_district("Karnataka", "Davangere"), ("Davanagere", "fuzzy"))

    def test_lookalikes_are_not_merged(self):
        # 'Korea' (Koriya) must not become 'Korba'; urban Bengaluru must not become the rural district
        self.assertEqual(gazetteer.resolve_district("Chhattisgarh", "Korea")[0], "Koriya")
        self.assertEqual(gazetteer.resolve_district("Karnataka", "Bangalore Urban")[0], "Bangalore")
        self.assertEqual(gazetteer.resolve_district("Kerala", "Atlantis"), (None, "none"))


class ForecastLeakageTests(unittest.TestCase):
    """Features at week t must be identical whatever happens after week t."""

    def setUp(self):
        self.gazetteer = pd.DataFrame({
            "state": ["S1", "S1", "S2"], "district": ["A", "B", "C"],
            "lat": [10.0, 11.0, 20.0], "lon": [75.0, 76.0, 80.0],
        })
        self.adjacency = pd.DataFrame({
            "origin_state": ["S1"], "origin_district": ["A"], "dest_state": ["S1"], "dest_district": ["B"],
        })
        first = date(2024, 1, 1)
        self.weeks = [first + timedelta(days=7 * i) for i in range(40)]
        rng = np.random.default_rng(0)
        rows = []
        for week in self.weeks:
            for state, district in (("S1", "A"), ("S1", "B"), ("S2", "C")):
                if rng.random() < 0.3:
                    rows.append({"WeekStart": week.isoformat(), "State": state, "District": district,
                                 "Disease": "Dengue", "Cases": int(rng.integers(1, 50))})
        self.outbreaks = pd.DataFrame(rows)

    def _panel(self, outbreaks, weeks):
        return Panel(outbreaks, self.gazetteer, self.adjacency, weeks, diseases=["Dengue"])

    def test_future_outbreaks_do_not_change_features(self):
        t = 25
        full = self._panel(self.outbreaks, self.weeks)
        cutoff = self.weeks[t].isoformat()
        past_only = self._panel(self.outbreaks[self.outbreaks["WeekStart"] <= cutoff], self.weeks)
        pd.testing.assert_frame_equal(full.features(t), past_only.features(t))

    def test_missing_bulletins_are_not_counted_as_quiet_weeks(self):
        covered = [w for i, w in enumerate(self.weeks) if not 10 <= i < 20]
        outbreaks = self.outbreaks[~self.outbreaks["WeekStart"].isin([w.isoformat() for w in self.weeks[10:20]])]
        panel = self._panel(outbreaks, covered)
        # 12-week window ending at week 21 holds only 2 covered weeks: the rate divides by 2, not 12
        events = panel.events[20:22].sum(axis=0)
        np.testing.assert_allclose(panel.features(21)["pair_rate_12w"].to_numpy(), (events / 2).reshape(-1), rtol=1e-6)
        # and a label is refused when the weeks it needs were never ingested
        self.assertFalse(panel.label_available(8))
        self.assertTrue(panel.label_available(25))


if __name__ == "__main__":
    unittest.main()
