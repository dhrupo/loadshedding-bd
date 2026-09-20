import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

import pdf_sources  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


class IdlePlantsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = pdf_sources.parse_bpdb_plants(FIXTURES / "bpdb_daily_2026-09-17.pdf", "2026-09-16")
        cls.by_name = {r["plant"]: r for r in cls.rows}

    def test_plant_short_of_gas(self):
        self.assertEqual(self.by_name["Ghorasal 365 MW CCPP Unit-7 Gas (PDB)"],
                         {"date": "2026-09-16", "plant": "Ghorasal 365 MW CCPP Unit-7 Gas (PDB)", "reason": "gas",
                          "lost_mw": 365, "remark": "Gas Shortage", "restart": ""})

    def test_plant_down_for_repairs(self):
        row = self.by_name["Matarbari 2*600 MW (CPGCL) Coal (CPGCL)"]
        self.assertEqual((row["reason"], row["lost_mw"], row["remark"]), ("repair", 506, "Under maint"))

    def test_coal_problems_are_their_own_reason(self):
        self.assertEqual(self.by_name["Barisal Electric 307 MW Coal (IPP)"]["reason"], "coal")
        self.assertEqual(self.by_name["Patuakhali 1320 MW (RNPL) Coal RPCL"]["reason"], "coal")

    def test_lost_power_adds_up_to_the_reports_own_totals(self):
        fuel = sum(r["lost_mw"] for r in self.rows if r["reason"] != "repair")
        repair = sum(r["lost_mw"] for r in self.rows if r["reason"] == "repair")
        self.assertEqual((fuel, repair), (4438, 2897))

    def test_running_plants_and_zone_totals_are_left_out(self):
        self.assertNotIn("Bibiyana-III 400 MW CCPP Gas (PDB)", self.by_name)
        self.assertFalse([r for r in self.rows if "Total" in r["plant"]])
        self.assertNotIn("Meghnaghat 450 MW CCPP(MPL) Gas (IPP)", self.by_name)


class IdlePlantRowsTest(unittest.TestCase):
    def parse(self, *rows):
        blank = [""] * 9
        original = pdf_sources.pdf_tables
        pdf_sources.pdf_tables = lambda _: [[sl, name, *blank[:7], limited, shut, remark, ""] for sl, name, limited, shut, remark in rows]
        try:
            return pdf_sources.parse_bpdb_plants(b"", "2026-09-16")
        finally:
            pdf_sources.pdf_tables = original

    def test_zero_in_the_shut_down_column_does_not_hide_a_fuel_shortage(self):
        rows = self.parse(("1", "Plant A Gas (PDB)", "150", "0", "Gas Shortage"))
        self.assertEqual([(r["reason"], r["lost_mw"]) for r in rows], [("gas", 150)])

    def test_both_columns_add_up_and_the_bigger_loss_names_the_reason(self):
        rows = self.parse(("1", "Plant A Gas (PDB)", "100", "200", "Unit-2 under maint."), ("2", "Plant B Gas (PDB)", "1,320", "", "Gas Shortage"))
        self.assertEqual([(r["reason"], r["lost_mw"]) for r in rows], [("repair", 300), ("gas", 1320)])


class BpdbDailyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual, cls.forecast = pdf_sources.parse_bpdb_daily(pdf_sources.pdf_text(FIXTURES / "bpdb_daily_2026-09-17.pdf"))

    def test_actuals_are_for_the_previous_day(self):
        self.assertEqual(self.actual["date"], "2026-09-16")

    def test_shortfall_causes_at_evening_peak(self):
        self.assertEqual(
            {k: self.actual[k] for k in ("gas_limit_mw", "coal_limit_mw", "water_limit_mw", "maintenance_mw")},
            {"gas_limit_mw": 4438, "coal_limit_mw": 107, "water_limit_mw": 0, "maintenance_mw": 2897},
        )

    def test_demand_loadshed_temperature_gas_energy(self):
        self.assertEqual(self.actual["eve_peak_demand_mw"], 17857)
        self.assertEqual(self.actual["eve_peak_loadshed_mw"], 1187)
        self.assertEqual(self.actual["max_temp_c"], 36)
        self.assertEqual(self.actual["gas_supplied_mmcfd"], 936)
        self.assertEqual(self.actual["energy_mkwh"], 360.22)

    def test_fuel_costs_add_up_to_published_total(self):
        parts = ("cost_gas_bdt", "cost_coal_bdt", "cost_oil_bdt", "cost_renewable_bdt", "cost_import_bdt")
        self.assertEqual(self.actual["cost_gas_bdt"], 465422791)
        self.assertEqual(self.actual["cost_total_bdt"], 3016775228)
        self.assertEqual(sum(self.actual[p] for p in parts), self.actual["cost_total_bdt"])

    def test_bpdb_forecast_for_report_day(self):
        self.assertEqual(self.forecast, {
            "date": "2026-09-17",
            "eve_peak_demand_mw": 18020.0,
            "eve_peak_generation_mw": 17060.0,
            "max_temp_c": 34.9,
        })

    def test_wrong_year_in_actual_line_is_taken_from_the_report_date(self):
        text = pdf_sources.pdf_text(FIXTURES / "bpdb_daily_2026-09-17.pdf").replace("Actual data of 16.09.26", "Actual data of 16.09.25")
        actual, _ = pdf_sources.parse_bpdb_daily(text)
        self.assertEqual(actual["date"], "2026-09-16")

    def test_actual_day_that_is_not_the_day_before_the_report_raises(self):
        text = pdf_sources.pdf_text(FIXTURES / "bpdb_daily_2026-09-17.pdf").replace("Actual data of 16.09.26", "Actual data of 14.09.26")
        with self.assertRaises(ValueError):
            pdf_sources.parse_bpdb_daily(text)

    def test_missing_label_raises(self):
        text = pdf_sources.pdf_text(FIXTURES / "bpdb_daily_2026-09-17.pdf").replace("Gas/LF limitation", "Other")
        with self.assertRaises(ValueError):
            pdf_sources.parse_bpdb_daily(text)


class PetrobanglaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = pdf_sources.parse_petrobangla(pdf_sources.pdf_text(FIXTURES / "petrobangla_2026-09-17.pdf"))

    def test_period_start_date(self):
        self.assertEqual(self.row["date"], "2026-09-17")

    def test_gas_to_power_demand_vs_supply(self):
        self.assertEqual(self.row["power_demand_mmcfd"], 2524.9)
        self.assertEqual(self.row["power_supply_mmcfd"], 927.8)
        self.assertEqual(self.row["fertilizer_demand_mmcfd"], 329.0)
        self.assertEqual(self.row["fertilizer_supply_mmcfd"], 151.9)
        self.assertEqual(self.row["total_supply_mmcfd"], 2551.2)

    def test_production_and_lng(self):
        self.assertEqual(self.row["production_capacity_mmcfd"], 3854)
        self.assertEqual(self.row["production_mmcfd"], 2600.1)
        self.assertEqual(self.row["rlng_mmcfd"], 982.1)

    def test_period_crossing_month_and_year(self):
        self.assertEqual(pdf_sources.period_start("Date : 30Sep-01Oct, 2026"), "2026-09-30")
        self.assertEqual(pdf_sources.period_start("Date : 31Dec-01Jan, 2026"), "2025-12-31")
        self.assertEqual(pdf_sources.period_start("Date : 17-18Sep, 2026"), "2026-09-17")

    def test_full_and_long_month_names(self):
        self.assertEqual(pdf_sources.period_start("Date : 21-22March, 2026 From 8.00 to 8.00"), "2026-03-21")
        self.assertEqual(pdf_sources.period_start("Date : 19-20July, 2026 From 8.00 to 8.00"), "2026-07-19")
        self.assertEqual(pdf_sources.period_start("Date : 30Sept-01October, 2026"), "2026-09-30")


class UnreadablePdfTest(unittest.TestCase):
    def test_broken_pdf_is_a_value_error_so_the_day_is_skipped_not_the_run(self):
        with self.assertRaises(ValueError):
            pdf_sources.pdf_text(b"%PDF-1.4 not really a pdf")


class NetworkErrorTest(unittest.TestCase):
    def test_one_failed_download_is_logged_and_the_rest_are_kept(self):
        import tempfile
        import urllib.error
        from datetime import date as real_date
        pdf = (FIXTURES / "bpdb_daily_2026-09-17.pdf").read_bytes()

        def fetch(url):
            if url.endswith("2026-09-16.pdf"):
                raise urllib.error.URLError("timed out")
            return pdf

        original = pdf_sources.ROOT, pdf_sources.fetch, pdf_sources.days_to_fetch
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            pdf_sources.ROOT, pdf_sources.fetch = Path(d), fetch
            pdf_sources.days_to_fetch = lambda have, today, days: [real_date(2026, 9, 15), real_date(2026, 9, 16)]
            errors = []
            try:
                pdf_sources.update_bpdb(2, 0, errors)
                saved = (Path(d) / "data" / "bpdb_daily.csv").read_text()
            finally:
                pdf_sources.ROOT, pdf_sources.fetch, pdf_sources.days_to_fetch = original
        self.assertEqual(len(errors), 1)
        self.assertIn("BPDB 2026-09-16", errors[0])
        self.assertIn("2026-09-16,", saved)


class UpdatePlantsTest(unittest.TestCase):
    def test_plants_follow_the_latest_daily_report_and_are_fetched_once(self):
        import tempfile
        pdf, fetched = (FIXTURES / "bpdb_daily_2026-09-17.pdf").read_bytes(), []

        def fetch(url):
            fetched.append(url)
            return pdf

        original = pdf_sources.ROOT, pdf_sources.fetch
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            (Path(d) / "data" / "bpdb_daily.csv").write_text("date,eve_peak_demand_mw\n2026-09-15,1\n2026-09-16,2\n")
            pdf_sources.ROOT, pdf_sources.fetch = Path(d), fetch
            try:
                pdf_sources.update_plants([])
                pdf_sources.update_plants([])
                saved = (Path(d) / "data" / "plants.csv").read_text()
            finally:
                pdf_sources.ROOT, pdf_sources.fetch = original
        self.assertEqual(len(fetched), 1)
        self.assertTrue(fetched[0].endswith("/2026-09-17.pdf"))
        self.assertIn("2026-09-16,Ghorasal 365 MW CCPP Unit-7 Gas (PDB),gas,365,Gas Shortage,", saved)


class PetrobanglaListTest(unittest.TestCase):
    def test_listing_yields_pdf_links_newest_first(self):
        links = pdf_sources.petrobangla_links((FIXTURES / "petrobangla_list.html").read_text(encoding="utf-8"))
        self.assertEqual(len(links), 10)
        self.assertTrue(links[0].endswith("f247bc06-9726-413e-b227-928cebb7b438.pdf"))


if __name__ == "__main__":
    unittest.main()
