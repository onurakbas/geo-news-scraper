"""
Scraper runner – launches all Scrapy spiders in a separate thread
so the FastAPI event loop is never blocked.

Usage:
    from app.services.scraper.runner import run_spiders_background
    asyncio.create_task(run_spiders_background())
"""

from __future__ import annotations

import asyncio
import threading
from enum import Enum

from loguru import logger


class ScrapeStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"


# Module-level state (single-process; sufficient for one-instance deployment)
_state = {
    "status": ScrapeStatus.IDLE,
    "last_run": None,      # ISO UTC string
    "last_error": None,    # error message or None
    "inserted": 0,
    "dropped": 0,
}


def get_scrape_state() -> dict:
    return dict(_state)


def is_running() -> bool:
    return _state["status"] == ScrapeStatus.RUNNING


async def _run_spiders_subprocess(spider_names: list[str]) -> None:
    """Run spiders in a separate process to avoid Twisted ReactorNotRestartable errors."""
    import sys
    import asyncio
    from datetime import datetime, timezone
    from pathlib import Path

    _state["status"] = ScrapeStatus.RUNNING
    _state["last_error"] = None
    logger.info(f"🕷️  Scraper started (subprocess) – spiders: {spider_names}")

    repo_root = Path(__file__).resolve().parents[4]
    script_path = repo_root / "scripts" / "run_spiders.py"

    try:
        # Run the existing scripts/run_spiders.py sequentially for each spider
        for name in spider_names:
            logger.info(f"🕷️ {name.replace('_', ' ').title()} sitesinden haberler çekilmeye başlandı...")
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script_path),
                name,
                cwd=str(repo_root),
                env={"PYTHONPATH": "backend"},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err_text = stderr.decode()
                _state["last_error"] = f"Spider {name} failed: {err_text[-500:]}"
                logger.error(f"💥 Scraper error on {name}:\n{err_text}")
                logger.error(f"Stdout:\n{stdout.decode()}")
                # Optional: you can break here if you want it to stop on first error
        
        if _state["last_error"] is None:
            _state["last_run"] = datetime.now(tz=timezone.utc).isoformat()
            logger.info("✅ Scraper subprocess finished.")
            # ── Auto-geocode: resolve districts → GPS coordinates ──────────
            logger.info("🗺️  Geocoding başlatılıyor – harita pinleri için koordinatlar hesaplanıyor...")
            try:
                geocode_script = repo_root / "scripts" / "run_geocode.py"
                gproc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(geocode_script),
                    cwd=str(repo_root),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                gout, gerr = await gproc.communicate()
                if gproc.returncode == 0:
                    logger.info(f"🗺️  Geocoding tamamlandı:\n{gout.decode()}")
                else:
                    logger.warning(f"⚠️  Geocoding hata ile bitti:\n{gerr.decode()[-500:]}")
            except Exception as gexc:
                logger.warning(f"⚠️  Geocoding başlatılamadı: {repr(gexc)}")
    except Exception as exc:
        import traceback
        _state["last_error"] = repr(exc)
        logger.error(f"💥 Scraper exception: {repr(exc)}")
        logger.error(traceback.format_exc())
    finally:
        _state["status"] = ScrapeStatus.IDLE


async def run_spiders_background(
    spider_names: list[str] | None = None,
) -> None:
    """
    Launch all (or a subset of) spiders gracefully via a subprocess.
    """
    if is_running():
        logger.warning("⚠️  Scrape already in progress – ignoring duplicate trigger.")
        return

    if spider_names is None:
        spider_names = [
            "cagdas_kocaeli",
            "ozgur_kocaeli",
            "ses_kocaeli",
            "yeni_kocaeli",
            "bizim_yaka",
        ]

    await _run_spiders_subprocess(spider_names)
