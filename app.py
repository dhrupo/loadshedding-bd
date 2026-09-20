"""Serve the dashboard with data that is checked against the sources on every request.

PGB (hourly) is re-checked before answering if the last check is older than LIVE_SECONDS.
Daily sources and the forecast are refreshed in the background so no request waits on them.
Run: uvicorn app:app
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import threading
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scraper"))

LIVE_SECONDS = 120
DAILY_SECONDS = 3600
NO_STORE = {"Cache-Control": "no-store"}
DATA_FILES = {
    "generation.csv", "demand.csv", "zones.csv", "fuel_prices.csv", "capacity.csv",
    "bpdb_daily.csv", "bpdb_forecast.csv", "gas.csv", "weather.csv", "forecast.json",
    "plants.csv", "tariff.csv", "alerts.json", "bmd_forecast.csv", "desco_schedule.json", "nesco_notices.csv",
}
log = logging.getLogger("loadshedding")


def _spawn(fn):
    threading.Thread(target=fn, daemon=True).start()


class Refresher:
    def __init__(self, live, daily, forecast, clock=time.monotonic, spawn=_spawn):
        self.live, self.daily, self.forecast = live, daily, forecast
        self.clock, self.spawn = clock, spawn
        self.live_lock = threading.Lock()
        self.running = {"daily": threading.Lock(), "forecast": threading.Lock()}
        self.last_live = self.last_daily = None
        self.status = {"live_checked_at": None, "live_error": None, "daily_checked_at": None}

    def ensure_live(self) -> None:
        if not self.live_lock.acquire(blocking=False):
            return
        try:
            if self.last_live is not None and self.clock() - self.last_live < LIVE_SECONDS:
                return
            try:
                new_rows = self.live()
                self.status["live_error"] = None
            except Exception as e:
                log.exception("live refresh failed")
                new_rows, self.status["live_error"] = 0, f"{type(e).__name__}: {e}"
            self.last_live = self.clock()
            self.status["live_checked_at"] = time.time()
        finally:
            self.live_lock.release()
        if new_rows:
            self._background("forecast", self.forecast)

    def ensure_daily(self) -> None:
        if self.last_daily is not None and self.clock() - self.last_daily < DAILY_SECONDS:
            return
        self.last_daily = self.clock()

        def run():
            self.daily()
            self.status["daily_checked_at"] = time.time()
            with self.running["forecast"]:
                self.forecast()

        self._background("daily", run)

    def _background(self, name: str, fn) -> None:
        lock = self.running[name]
        if not lock.acquire(blocking=False):
            return

        def run():
            try:
                fn()
            except Exception:
                log.exception("%s refresh failed", name)
            finally:
                lock.release()

        self.spawn(run)


def create_app(refresher: Refresher, data_dir: Path, index: Path, static_dir: Path) -> FastAPI:
    app = FastAPI(title="Loadshedding BD", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.get("/")
    def page():
        return FileResponse(index, headers=NO_STORE)

    @app.get("/data/{name}")
    def data(name: str):
        if name not in DATA_FILES or not (data_dir / name).is_file():
            raise HTTPException(404)
        refresher.ensure_live()
        refresher.ensure_daily()
        return FileResponse(data_dir / name, headers=NO_STORE)

    @app.get("/api/status")
    def status():
        refresher.ensure_live()
        return {**refresher.status, "server_time": time.time()}

    @app.middleware("http")
    async def no_store(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


def _daily_jobs():
    import bmd
    import pdf_sources
    import sources
    import utilities
    import weather
    for job in (sources.update, pdf_sources.update, weather.update, bmd.update, utilities.update):
        try:
            for error in job() or []:
                log.warning("%s: %s", job.__module__, error)
        except Exception:
            log.exception("%s failed", job.__module__)


def _live_job():
    import pgb
    return pgb.update(timeout=20, attempts=1)


def _forecast_job():
    import forecast
    forecast.update()


app = create_app(Refresher(_live_job, _daily_jobs, _forecast_job), ROOT / "data", ROOT / "index.html", ROOT / "static")
