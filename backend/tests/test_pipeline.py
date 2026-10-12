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
from data import clean_data, pdf_extractor, scraper


class ExtractorTests(unittest.TestCase):
    def test_row_with_reporting_date(self):
        row = ["AP/GUN/2025/45/1997", "Andhra Pradesh", "Guntur", "Acute Diarrhoeal\nDisease", "457", "0",
               "04-11- 2025", "04-11- 2025", "Under Control", "Cases of vomiting and loose stools"]
        record = pdf_extractor._parse_row(row)
        self.assertEqual(record["outbreak_id"], "AP/GUN/2025/45/1997")
        self.assertEqual(record["_id_kind"], "idsp")
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

    def test_ids_without_a_year_and_unnumbered_rows(self):
        short = pdf_extractor._parse_row(["AR/PPM/36/1225", "Arunachal Pradesh", "Papumpare", "Japanese Encephalitis",
                                          "05", "00", "08-05-18", "31-08-18", "Under Surveillance", "Cases reported"])
        self.assertEqual((short["outbreak_id"], short["_id_kind"]), ("AR/PPM/36/1225", "short"))
        serial = pdf_extractor._parse_row(["2.", "Tamil Nadu", "Ramanathapuram", "Dengue", "21", "00",
                                           "15-10-20", "26-10-20", "Under Control", "Cases reported"])
        self.assertEqual((serial["_id_kind"], serial["district"], serial["cases"]), ("serial", "Ramanathapuram", "21"))
        # A numbered line of ordinary text is not an outbreak
        self.assertIsNone(pdf_extractor._parse_row(["1.", "Reporting status", "", "", "", "", ""]))

    def test_cover_week_and_nil_statement(self):
        self.assertEqual(pdf_extractor._cover_week("alerts/outbreaks reported in the 38th week 2020", None), (2020, 38))
        self.assertEqual(pdf_extractor._cover_week("no week printed", date(2025, 7, 13)), (2025, 28))
        self.assertTrue(pdf_extractor.NIL_PATTERN.search("During the week 38th there were no outbreaks reported from States"))
        self.assertFalse(pdf_extractor.NIL_PATTERN.search("Outbreaks reported and responded to by States"))

    def test_non_outbreak_rows_are_ignored(self):
        self.assertIsNone(pdf_extractor._parse_row(["Unique ID.", "Name of State/UT", "Name of District"]))
        self.assertIsNone(pdf_extractor._parse_row(["No. of States/UT's Submitted outbreak report", None, "31"]))

    def test_week_range_on_cover(self):
        start, end = pdf_extractor._parse_week_range("28th Week (7th July 2025 to 13th July 2025)")
        self.assertEqual((start, end), (date(2025, 7, 7), date(2025, 7, 13)))
        start, end = pdf_extractor._parse_week_range("29th December to 4th January 2026")
        self.assertEqual((start, end), (date(2025, 12, 29), date(2026, 1, 4)))


class ScraperTests(unittest.TestCase):
    INDEX = """
      <table>
        <tr><th>YEAR</th><th>WEEKS</th></tr>
        <tr><td>2026</td><td>
          <a href="https://idsp.mohfw.gov.in/WriteReadData/l892s/111.pdf">1st</a>
          <a href="WriteReadData/l892s/222.pdf">2nd</a></td></tr>
        <tr><td>2024</td><td>
          <a href="https://drive.google.com/file/d/1S-Nw1WSp_GngcPFZt354ebS8VPBD-DI9/view?usp=sharing">13th</a>
          <a href="https://example.org/not-a-bulletin.html">14th</a></td></tr>
        <tr><td>Archive</td><td><a href="old.pdf">1st</a></td></tr>
      </table>"""

    def test_index_gives_year_week_and_url(self):
        rows = scraper.parse_index(self.INDEX)
        self.assertEqual([(y, w) for y, w, _ in rows], [(2026, 1), (2026, 2), (2024, 13)])
        self.assertTrue(rows[1][2].startswith("https://") and rows[1][2].endswith("/WriteReadData/l892s/222.pdf"))  # relative link resolved

    def test_ncdc_index_layout(self):
        html = """<a href="/uploads/weekly_outbreaks/2026/week30_1789731731.pdf">Week 30</a>
                  <a href="/uploads/weekly_outbreaks/2009/week48.pdf">Week 48</a>
                  <a href="/uploads/other/report.pdf">Annual report</a>"""
        rows = scraper.parse_index(html)
        self.assertEqual([(y, w) for y, w, _ in rows], [(2026, 30), (2009, 48)])
        self.assertTrue(rows[0][2].endswith("/uploads/weekly_outbreaks/2026/week30_1789731731.pdf"))

    def test_google_drive_links(self):
        self.assertEqual(scraper._drive_file_id(scraper.parse_index(self.INDEX)[2][2]),
                         "1S-Nw1WSp_GngcPFZt354ebS8VPBD-DI9")
        self.assertIsNone(scraper._drive_file_id("https://drive.google.com/drive/folders/"))

    def test_incomplete_pdf_is_rejected(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as folder:
            good, truncated, page = (os.path.join(folder, n) for n in ("a.pdf", "b.pdf", "c.pdf"))
            open(good, "wb").write(b"%PDF-1.7\n...\n%%EOF\n")
            open(truncated, "wb").write(b"%PDF-1.7\n...")
            open(page, "wb").write(b"<html>Service unavailable</html>")
            self.assertTrue(scraper.is_complete_pdf(good))
            self.assertFalse(scraper.is_complete_pdf(truncated))
            self.assertFalse(scraper.is_complete_pdf(page))


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

    def test_rows_without_an_idsp_id_are_kept_under_a_synthetic_id(self):
        raw = pd.DataFrame([{"outbreak_id": "NOID/2020/43/1", "state": "Maharashtra", "district": "Ahmednagar",
                             "disease": "Food Poisoning", "cases": "45", "deaths": "00", "start_date": "17-10-20",
                             "report_date": "19-10-20", "status": "Under Control", "comments": "",
                             "bulletin_year": "2020", "bulletin_week": "43", "week_start": "", "week_end": "",
                             "source_file": "x.pdf"}])
        clean, _ = clean_data.build_clean_frame(raw)
        row = clean.iloc[0]
        self.assertEqual((row["ReportYear"], row["ReportWeek"], row["District"], row["Cases"]), (2020, 43, "Ahmadnagar", 45))
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
