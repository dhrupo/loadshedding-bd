import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

import pgb  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def fixture(name):
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


class ParseGenerationTest(unittest.TestCase):
    def test_first_row_matches_published_values(self):
        rows = pgb.parse(fixture("generation"), pgb.GENERATION)
        self.assertEqual(rows[0], {
            "timestamp": "2026-09-19T11:00",
            "generation_mw": 13906,
            "gas": 5519,
            "liquid_fuel": 810,
            "coal": 4744,
            "hydro": 218,
            "solar": 666,
            "wind": 0,
            "india_bheramara_hvdc": 891,
            "india_tripura": 34,
            "india_adani": 1024,
            "nepal": 0,
            "remarks": "",
        })

    def test_commented_out_columns_are_ignored(self):
        rows = pgb.parse(fixture("generation"), pgb.GENERATION)
        self.assertEqual(list(rows[0]), ["timestamp", *pgb.GENERATION["fields"], "remarks"])

    def test_rows_are_newest_first_and_unique(self):
        stamps = [r["timestamp"] for r in pgb.parse(fixture("generation"), pgb.GENERATION)]
        self.assertEqual(stamps, sorted(set(stamps), reverse=True))


class ParseDemandTest(unittest.TestCase):
    def test_first_row_matches_published_values(self):
        rows = pgb.parse(fixture("demand"), pgb.DEMAND)
        self.assertEqual(rows[0], {
            "timestamp": "2026-09-19T11:00",
            "demand_mw": 13791,
            "supply_mw": 13456,
            "loadshed_mw": 335,
            "remarks": "",
        })

    def test_page_past_the_end_yields_no_rows(self):
        self.assertEqual(pgb.parse(fixture("empty"), pgb.DEMAND), [])


class LayoutGuardTest(unittest.TestCase):
    def test_changed_header_raises_instead_of_mislabelling(self):
        html = fixture("demand")
        start = html.index("<table")
        html = html[:start] + html[start:].replace("লোডশেড", "অন্য", 1)
        with self.assertRaises(ValueError):
            pgb.parse(html, pgb.DEMAND)


class NumberTest(unittest.TestCase):
    def test_bangla_digits_blanks_and_decimals(self):
        self.assertEqual(pgb.number("১৩৪০৫"), 13405)
        self.assertEqual(pgb.number("-১৩৪০৫.৫০"), -13405.5)
        self.assertIsNone(pgb.number(""))
        self.assertIsNone(pgb.number("—"))

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            pgb.number("N/A")


class MergeTest(unittest.TestCase):
    def test_new_values_replace_revised_hours_and_output_is_sorted(self):
        old = [{"timestamp": "2026-09-19T09:00", "v": 1}, {"timestamp": "2026-09-19T10:00", "v": 1}]
        new = [{"timestamp": "2026-09-19T11:00", "v": 3}, {"timestamp": "2026-09-19T10:00", "v": 2}]
        self.assertEqual(pgb.merge(old, new), [
            {"timestamp": "2026-09-19T09:00", "v": 1},
            {"timestamp": "2026-09-19T10:00", "v": 2},
            {"timestamp": "2026-09-19T11:00", "v": 3},
        ])


class CrawlTest(unittest.TestCase):
    def pages(self, *stamps_per_page):
        return {i + 1: [{"timestamp": s} for s in stamps] for i, stamps in enumerate(stamps_per_page)}

    def test_stops_after_page_reaching_cutoff(self):
        pages = self.pages(["2026-09-19T11:00", "2026-09-19T10:00"],
                           ["2026-09-19T09:00", "2026-09-19T08:00"],
                           ["2026-09-19T07:00"])
        fetched = []

        def fetch(page):
            fetched.append(page)
            return pages.get(page, [])

        rows = pgb.crawl(fetch, cutoff="2026-09-19T09:00", max_pages=10, delay=0)
        self.assertEqual(fetched, [1, 2])
        self.assertEqual([r["timestamp"] for r in rows],
                         ["2026-09-19T11:00", "2026-09-19T10:00", "2026-09-19T09:00"])

    def test_stops_on_empty_page_and_on_max_pages(self):
        pages = self.pages(["2026-09-19T11:00"], ["2026-09-19T10:00"], ["2026-09-19T09:00"])
        self.assertEqual(len(pgb.crawl(lambda p: pages.get(p, []), "2000-01-01T00:00", 10, 0)), 3)
        self.assertEqual(len(pgb.crawl(lambda p: pages.get(p, []), "2000-01-01T00:00", 2, 0)), 2)


class CutoffTest(unittest.TestCase):
    def test_resumes_from_latest_saved_hour(self):
        rows = [{"timestamp": "2026-09-18T23:00"}, {"timestamp": "2026-09-19T11:00"}]
        self.assertEqual(pgb.cutoff(rows, datetime(2026, 9, 19, 12), 365), "2026-09-19T11:00")

    def test_empty_file_backfills_requested_days(self):
        self.assertEqual(pgb.cutoff([], datetime(2026, 9, 19, 12), 365), "2025-09-19T12:00")


class TlsTest(unittest.TestCase):
    def test_context_trusts_missing_gov_intermediates_and_still_verifies(self):
        import ssl
        context = pgb.tls_context()
        issuers = [dict(item[0] for item in c["subject"]).get("commonName") for c in context.get_ca_certs()]
        self.assertIn("SSL2BUY EMEA RSA Domain Validation Secure Server CA", issuers)
        self.assertIn("Sectigo Public Server Authentication CA DV R36", issuers)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)


class UpdateTest(unittest.TestCase):
    def test_update_fetches_both_tables_writes_csvs_and_counts_new_rows(self):
        import tempfile
        pages = {pgb.GENERATION["url"]: fixture("generation"), pgb.DEMAND["url"]: fixture("demand")}
        original_root, original_get = pgb.ROOT, pgb.get
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            pgb.ROOT = Path(d)
            pgb.get = lambda url, **kw: pages[url.split("?")[0]]
            try:
                count = pgb.update(days=3650, max_pages=1, delay=0)
            finally:
                pgb.ROOT, pgb.get = original_root, original_get
            self.assertEqual(count, 102)
            self.assertEqual(len(pgb.read_csv(Path(d) / "data" / "demand.csv")), 51)
            self.assertEqual(len(pgb.read_csv(Path(d) / "data" / "generation.csv")), 51)


class QuickFetchTest(unittest.TestCase):
    def test_update_can_use_a_short_timeout_and_single_attempt(self):
        import tempfile
        calls = []
        pages = {pgb.GENERATION["url"]: fixture("generation"), pgb.DEMAND["url"]: fixture("demand")}
        original_root, original_get = pgb.ROOT, pgb.get
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            pgb.ROOT = Path(d)
            pgb.get = lambda url, **kw: calls.append(kw) or pages[url.split("?")[0]]
            try:
                pgb.update(days=3650, max_pages=1, delay=0, timeout=20, attempts=1)
            finally:
                pgb.ROOT, pgb.get = original_root, original_get
        self.assertTrue(calls and all(kw == {"timeout": 20, "attempts": 1} for kw in calls))


class CsvRoundTripTest(unittest.TestCase):
    def test_blank_cells_stay_blank_not_zero(self):
        import tempfile
        rows = [{"timestamp": "2015-04-19T21:00", "solar": None, "wind": 0, "remarks": ""}]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.csv"
            pgb.write_csv(path, rows, ["timestamp", "solar", "wind", "remarks"])
            self.assertEqual(path.read_text().splitlines()[1], "2015-04-19T21:00,,0,")
            self.assertEqual(pgb.read_csv(path)[0]["timestamp"], "2015-04-19T21:00")


if __name__ == "__main__":
    unittest.main()
