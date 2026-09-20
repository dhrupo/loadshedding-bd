import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import app as server  # noqa: E402


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Jobs:
    def __init__(self, live_result=0, live_error=None):
        self.calls = {"live": 0, "daily": 0, "forecast": 0}
        self.live_result, self.live_error = live_result, live_error

    def live(self):
        self.calls["live"] += 1
        if self.live_error:
            raise self.live_error
        return self.live_result

    def daily(self):
        self.calls["daily"] += 1

    def forecast(self):
        self.calls["forecast"] += 1


class ServerTest(unittest.TestCase):
    def make(self, jobs, clock=None):
        self.data = Path(tempfile.mkdtemp())
        (self.data / "demand.csv").write_text("timestamp,demand_mw\n2026-09-19T11:00,13791\n")
        self.static = Path(tempfile.mkdtemp())
        (self.static / "app.js").write_text("console.log(1)")
        self.clock = clock or Clock()
        refresher = server.Refresher(jobs.live, jobs.daily, jobs.forecast, clock=self.clock, spawn=lambda fn: fn())
        return TestClient(server.create_app(refresher, self.data, ROOT / "index.html", self.static))

    def test_static_files_are_served_uncached_without_touching_sources(self):
        jobs = Jobs()
        client = self.make(jobs)
        response = client.get("/static/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(jobs.calls["live"], 0)

    def test_large_files_are_sent_compressed(self):
        client = self.make(Jobs())
        (self.static / "places.json").write_text("[" + ",".join(['{"name":"Mirpur 2"}'] * 2000) + "]")
        response = client.get("/static/places.json", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(response.headers.get("content-encoding"), "gzip")
        self.assertIn("Mirpur 2", response.text)

    def test_static_cannot_escape_its_folder(self):
        client = self.make(Jobs())
        for path in ("/static/../app.py", "/static/..%2F..%2Fapp.py", "/static/missing.js"):
            self.assertEqual(client.get(path).status_code, 404, path)

    def test_first_request_fetches_live_data_before_answering(self):
        jobs = Jobs()
        client = self.make(jobs)
        response = client.get("/data/demand.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("13791", response.text)
        self.assertEqual(jobs.calls["live"], 1)

    def test_requests_within_two_minutes_reuse_the_check(self):
        jobs = Jobs()
        client = self.make(jobs)
        client.get("/data/demand.csv")
        self.clock.now += 119
        client.get("/data/demand.csv")
        self.assertEqual(jobs.calls["live"], 1)
        self.clock.now += 2
        client.get("/data/demand.csv")
        self.assertEqual(jobs.calls["live"], 2)

    def test_new_pgb_rows_trigger_a_forecast_rebuild(self):
        jobs = Jobs(live_result=3)
        self.make(jobs).get("/data/demand.csv")
        self.assertGreaterEqual(jobs.calls["forecast"], 1)

    def test_no_new_rows_no_forecast_rebuild_from_live(self):
        jobs = Jobs(live_result=0)
        client = self.make(jobs)
        client.get("/data/demand.csv")
        before = jobs.calls["forecast"]
        self.clock.now += 200
        client.get("/data/demand.csv")
        self.assertEqual(jobs.calls["forecast"], before)

    def test_pgb_down_still_serves_stored_data_and_reports_it(self):
        jobs = Jobs(live_error=OSError("connection reset"))
        client = self.make(jobs)
        self.assertEqual(client.get("/data/demand.csv").status_code, 200)
        status = client.get("/api/status").json()
        self.assertIn("connection reset", status["live_error"])

    def test_daily_sources_refresh_at_most_hourly(self):
        jobs = Jobs()
        client = self.make(jobs)
        client.get("/data/demand.csv")
        self.clock.now += 1800
        client.get("/data/demand.csv")
        self.assertEqual(jobs.calls["daily"], 1)
        self.clock.now += 1801
        client.get("/data/demand.csv")
        self.assertEqual(jobs.calls["daily"], 2)

    def test_responses_are_never_cached(self):
        client = self.make(Jobs())
        for path in ("/", "/data/demand.csv", "/api/status"):
            self.assertEqual(client.get(path).headers["cache-control"], "no-store")

    def test_only_known_data_files_are_served(self):
        client = self.make(Jobs())
        for path in ("/data/secret.txt", "/data/..%2Fapp.py", "/data/../app.py"):
            self.assertEqual(client.get(path).status_code, 404, path)

    def test_public_help_files_are_served(self):
        client = self.make(Jobs())
        for name in ("plants.csv", "tariff.csv", "alerts.json", "bmd_forecast.csv", "desco_schedule.json", "nesco_notices.csv"):
            (self.data / name).write_text("x")
            self.assertEqual(client.get(f"/data/{name}").status_code, 200, name)

    def test_daily_refresh_rebuilds_the_forecast_under_the_forecast_lock(self):
        seen = []
        jobs = Jobs()
        refresher = server.Refresher(jobs.live, jobs.daily, lambda: seen.append(refresher.running["forecast"].locked()),
                                     clock=Clock(), spawn=lambda fn: fn())
        refresher.ensure_daily()
        self.assertEqual(seen, [True])

    def test_requests_during_a_slow_live_fetch_do_not_wait(self):
        import time as _time
        release = threading.Event()
        jobs = Jobs()
        refresher = server.Refresher(lambda: release.wait(5) and 0, jobs.daily, jobs.forecast, clock=Clock(), spawn=lambda fn: None)
        first = threading.Thread(target=refresher.ensure_live)
        first.start()
        _time.sleep(0.1)
        started = _time.monotonic()
        refresher.ensure_live()
        waited = _time.monotonic() - started
        release.set()
        first.join()
        self.assertLess(waited, 0.5)

    def test_concurrent_requests_share_one_live_fetch(self):
        release = threading.Event()
        jobs = Jobs()
        slow_live = jobs.live

        def live():
            release.wait(2)
            return slow_live()

        refresher = server.Refresher(live, jobs.daily, jobs.forecast, clock=Clock(), spawn=lambda fn: None)
        threads = [threading.Thread(target=refresher.ensure_live) for _ in range(5)]
        for t in threads:
            t.start()
        release.set()
        for t in threads:
            t.join()
        self.assertEqual(jobs.calls["live"], 1)


if __name__ == "__main__":
    unittest.main()
