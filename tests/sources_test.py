import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

import sources  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def fixture(name):
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


class ZonesTest(unittest.TestCase):
    def test_nine_zones_for_the_requested_date(self):
        rows = sources.parse_zones(fixture("bpdb_area"), "2026-09-13")
        self.assertEqual(len(rows), 9)
        self.assertEqual(rows[0], {"date": "2026-09-13", "zone": "Dhaka", "demand_mw": 6266, "loadshed_mw": 242})
        self.assertEqual(rows[-1]["zone"], "Rangpur")

    def test_js_filled_total_row_is_not_kept(self):
        zones = [r["zone"] for r in sources.parse_zones(fixture("bpdb_area"), "2026-09-13")]
        self.assertNotIn("Total", zones)

    def test_date_without_data_yields_nothing(self):
        self.assertEqual(sources.parse_zones(fixture("bpdb_area_missing"), "2026-09-18"), [])

    def test_changed_columns_raise(self):
        html = fixture("bpdb_area").replace("Load shed (MW)", "Something else")
        with self.assertRaises(ValueError):
            sources.parse_zones(html, "2026-09-13")


class DaysToFetchTest(unittest.TestCase):
    def test_empty_history_backfills_the_requested_days(self):
        from datetime import date
        days = sources.days_to_fetch(set(), date(2026, 9, 19), days=3)
        self.assertEqual([str(d) for d in days], ["2026-09-16", "2026-09-17", "2026-09-18", "2026-09-19"])

    def test_new_days_plus_recent_gaps_are_fetched(self):
        from datetime import date
        have = {"2026-09-10", "2026-09-11", "2026-09-13", "2026-09-14"}
        days = sources.days_to_fetch(have, date(2026, 9, 16), days=365, recheck=7)
        self.assertEqual([str(d) for d in days], ["2026-09-09", "2026-09-12", "2026-09-15", "2026-09-16"])

    def test_old_gaps_outside_the_recheck_window_are_left_alone(self):
        from datetime import date
        have = {"2026-08-01", "2026-08-03", "2026-09-15"}
        days = sources.days_to_fetch(have, date(2026, 9, 16), days=365, recheck=2)
        self.assertEqual([str(d) for d in days], ["2026-09-14", "2026-09-16"])


class FuelPricesTest(unittest.TestCase):
    def setUp(self):
        self.rows = {r["product"]: r for r in sources.parse_fuel_prices(fixture("bpc_prices"))}

    def test_power_plant_fuels_with_effective_dates(self):
        self.assertEqual(self.rows["furnace_oil"], {"effective_date": "2026-09-07", "product": "furnace_oil", "price_bdt": 96.86, "unit": "litre"})
        self.assertEqual(self.rows["diesel"], {"effective_date": "2026-06-01", "product": "diesel", "price_bdt": 115.0, "unit": "litre"})

    def test_household_fuels_are_included(self):
        self.assertEqual(self.rows["octane"], {"effective_date": "2026-06-01", "product": "octane", "price_bdt": 145.0, "unit": "litre"})
        self.assertEqual(self.rows["petrol"]["price_bdt"], 140.0)
        self.assertEqual(self.rows["kerosene"]["price_bdt"], 135.0)

    def test_government_lpg_is_priced_per_cylinder(self):
        self.assertEqual(self.rows["lpg_12_5kg"], {"effective_date": "2026-02-23", "product": "lpg_12_5kg", "price_bdt": 776.93, "unit": "cylinder"})

    def test_only_known_products_are_kept(self):
        self.assertTrue(set(self.rows) <= set(sources.FUEL_PRODUCTS.values()))
        self.assertIn("ldo", self.rows)


class TariffTest(unittest.TestCase):
    def setUp(self):
        self.rows = sources.parse_tariff(fixture("dpdc_tariff"))

    def test_home_slabs_in_order_with_rates(self):
        self.assertEqual([(r["kind"], r["from_units"], r["to_units"], r["rate_bdt"]) for r in self.rows], [
            ("lifeline", 0, 50, 4.63), ("slab", 0, 75, 5.26), ("slab", 76, 200, 8.5), ("slab", 201, 300, 9.1),
            ("slab", 301, 400, 9.62), ("slab", 401, 600, 15.01), ("slab", 601, "", 17.35),
        ])

    def test_effective_month_and_demand_charge(self):
        self.assertEqual({(r["effective"], r["demand_bdt_kw"]) for r in self.rows}, {("2026-06", 42.0)})

    def test_medium_voltage_home_rates_are_never_mistaken_for_the_household_slabs(self):
        with self.assertRaises(ValueError):
            sources.parse_tariff(fixture("dpdc_tariff").replace("এলটি- এ", "অন্য- এ"))

    def test_slab_without_unit_numbers_is_a_layout_error(self):
        with self.assertRaises(ValueError):
            sources.parse_tariff(fixture("dpdc_tariff").replace("লাইফ লাইন: ০০-৫০ ইউনিট", "লাইফ লাইন"))

    def test_missing_home_section_raises(self):
        with self.assertRaises(ValueError):
            sources.parse_tariff(fixture("dpdc_tariff").replace("আবাসিক", "অন্য"))


class UpdateTest(unittest.TestCase):
    def test_one_failing_source_does_not_stop_the_others(self):
        calls, names = [], ("update_zones", "update_fuel_prices", "update_capacity", "update_tariff")
        original = {n: getattr(sources, n) for n in names}

        def failing(*_):
            raise ValueError("BPC fuel prices: table layout changed")

        for n in names:
            setattr(sources, n, (lambda name: lambda *_: calls.append(name))(n))
        sources.update_fuel_prices = failing
        try:
            errors = sources.update(1, 0)
        finally:
            for n, fn in original.items():
                setattr(sources, n, fn)
        self.assertEqual(calls, ["update_zones", "update_capacity", "update_tariff"])
        self.assertEqual(len(errors), 1)
        self.assertIn("table layout changed", errors[0])


class CapacityTest(unittest.TestCase):
    def test_installed_capacity_by_fuel(self):
        rows = sources.parse_capacity(fixture("sreda_mix"), "2026-09-19")
        self.assertEqual(rows, [
            {"as_of": "2026-09-19", "fuel": "coal", "installed_mw": 6273.0},
            {"as_of": "2026-09-19", "fuel": "gas", "installed_mw": 12472.0},
            {"as_of": "2026-09-19", "fuel": "hfo", "installed_mw": 5641.0},
            {"as_of": "2026-09-19", "fuel": "hsd", "installed_mw": 768.0},
            {"as_of": "2026-09-19", "fuel": "imported", "installed_mw": 2696.0},
            {"as_of": "2026-09-19", "fuel": "renewable", "installed_mw": 1852.14},
            {"as_of": "2026-09-19", "fuel": "captive", "installed_mw": 2800.0},
        ])

    def test_unchanged_snapshot_is_not_appended_again(self):
        old = sources.parse_capacity(fixture("sreda_mix"), "2026-09-18")
        new = sources.parse_capacity(fixture("sreda_mix"), "2026-09-19")
        self.assertEqual(sources.append_if_changed(old, new, "as_of"), old)

    def test_changed_snapshot_is_appended(self):
        old = sources.parse_capacity(fixture("sreda_mix"), "2026-09-18")
        new = sources.parse_capacity(fixture("sreda_mix"), "2026-09-19")
        new[0] = {**new[0], "installed_mw": 6500.0}
        self.assertEqual(sources.append_if_changed(old, new, "as_of"), old + new)


if __name__ == "__main__":
    unittest.main()
