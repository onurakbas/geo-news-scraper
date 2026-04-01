"""
Scraper runner – launches all Scrapy spiders in parallel subprocesses
so the FastAPI event loop is never blocked and total runtime equals
the slowest individual spider rather than their sum.

Usage:
    from app.services.scraper.runner import run_spiders_background
    asyncio.create_task(run_spiders_background())
"""

from __future__ import annotations

import asyncio
import time
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


async def _reset_news_collection() -> None:
    """Wipe the news collection before a fresh scrape run."""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    import pymongo

    root = Path(__file__).resolve().parents[4]
    load_dotenv(root / ".env")

    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name   = os.getenv("MONGODB_DB_NAME", "geo_news")

    try:
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        result = client[db_name]["news"].delete_many({})
        logger.info(f"🗑️  DB reset: {result.deleted_count} eski haber silindi.")
        client.close()
    except Exception as exc:
        logger.warning(f"⚠️  DB reset başarısız: {repr(exc)}")


async def _run_one_spider(name: str, script_path, repo_root) -> tuple[str, int, float]:
    """Run a single spider subprocess; return (name, returncode, elapsed_secs)."""
    import sys

    t0 = time.monotonic()
    logger.info(f"🕷️  [{name}] → başladı")

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
    elapsed = time.monotonic() - t0

    if proc.returncode == 0:
        logger.info(f"✅ [{name}] → tamamlandı ({elapsed:.0f}s / {elapsed/60:.1f}dk)")
    else:
        err = stderr.decode()[-500:]
        logger.error(f"💥 [{name}] → HATA ({elapsed:.0f}s)\n{err}")

    return name, proc.returncode, elapsed


async def _run_spiders_subprocess(spider_names: list[str]) -> None:
    """Run ALL spiders in parallel via asyncio.gather, then auto-geocode."""
    import sys
    from datetime import datetime, timezone
    from pathlib import Path

    _state["status"] = ScrapeStatus.RUNNING
    _state["last_error"] = None

    repo_root   = Path(__file__).resolve().parents[4]
    script_path = repo_root / "scripts" / "run_spiders.py"

    logger.info(
        f"🚀 Scraper başlatılıyor – {len(spider_names)} site PARALEL çalışacak: {spider_names}"
    )

    try:
        # ── 1. Eski haberleri temizle ─────────────────────────────────────────
        await _reset_news_collection()

        # ── 2. Tüm spider'ları aynı anda başlat ──────────────────────────────
        t_wall = time.monotonic()
        tasks = [_run_one_spider(n, script_path, repo_root) for n in spider_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_elapsed = time.monotonic() - t_wall

        # ── 3. Özet rapor ─────────────────────────────────────────────────────
        errors = []
        lines = [f"\n── Scrape Summary {'─'*35}"]
        lines.append(f"  Toplam süre (duvar saati) : {total_elapsed:.0f}s  ({total_elapsed/60:.1f}dk)")
        lines.append(f"  {'Site':<22} {'Süre':>6}  Durum")
        lines.append(f"  {'─'*40}")
        for r in results:
            if isinstance(r, Exception):
                errors.append(repr(r))
                lines.append(f"  {'???':<22} HATA  ❌  {repr(r)[:40]}")
            else:
                name, rc, elapsed = r
                status = "✅" if rc == 0 else "❌"
                lines.append(f"  {name:<22} {elapsed:>5.0f}s  {status}")
                if rc != 0:
                    errors.append(f"{name} → return code {rc}")
        lines.append(f"{'─'*55}\n")
        logger.info("\n".join(lines))

        if errors:
            _state["last_error"] = "; ".join(errors)

        # ── 4. Geocoding ──────────────────────────────────────────────────────
        _state["last_run"] = datetime.now(tz=timezone.utc).isoformat()
        logger.info("🗺️  Geocoding başlatılıyor – koordinatlar hesaplanıyor...")
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
                logger.warning(f"⚠️  Geocoding hata:\n{gerr.decode()[-500:]}")
        except Exception as gexc:
            logger.warning(f"⚠️  Geocoding başlatılamadı: {repr(gexc)}")

        # ── 5. DB Özeti ───────────────────────────────────────────────────────
        try:
            import os, pymongo
            from dotenv import load_dotenv
            root2 = Path(__file__).resolve().parents[4]
            load_dotenv(root2 / ".env")
            cli = pymongo.MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=3000)
            col = cli[os.getenv("MONGODB_DB_NAME", "geo_news")]["news"]

            VALID_CATS = {"Trafik Kazası", "Yangın", "Elektrik Kesintisi", "Hırsızlık", "Kültürel Etkinlikler"}

            total         = col.count_documents({})
            with_coords   = col.count_documents({"coordinates": {"$ne": None}})
            map_visible   = col.count_documents({"coordinates": {"$ne": None}, "type": {"$in": list(VALID_CATS)}})
            cat_counts    = list(col.aggregate([
                {"$group": {"_id": "$type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]))
            src_counts    = list(col.aggregate([
                {"$group": {"_id": "$source", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]))
            cli.close()

            db_lines = [f"\n── DB Summary {'─'*40}"]
            db_lines.append(f"  Toplam haber      : {total}")
            db_lines.append(f"  Koordinatlı       : {with_coords}  ({100*with_coords//total if total else 0}%)")
            db_lines.append(f"  Koordinatsız      : {total - with_coords}")
            db_lines.append(f"  Haritada görünür  : {map_visible}  (koordinat + zorunlu kategori)")
            db_lines.append(f"  Haritada görünmez : {with_coords - map_visible}  (koordinat var ama 'Diğer' kategorisi)")
            db_lines.append(f"  {'─'*52}")
            db_lines.append(f"  {'Kaynak (Site)':<24} {'Adet':>4}")
            db_lines.append(f"  {'─'*30}")
            for row in src_counts:
                db_lines.append(f"  {(row['_id'] or '?'):<24} {row['count']:>4}")
            db_lines.append(f"  {'─'*52}")
            db_lines.append(f"  {'Kategori':<28} {'Adet':>4}   Bar  (🗺️=haritaya yansır)")
            db_lines.append(f"  {'─'*52}")
            for row in cat_counts:
                cat      = row["_id"] or "Bilinmiyor"
                cnt      = row["count"]
                pct      = 100 * cnt // total if total else 0
                bar      = "█" * (cnt * 20 // (total or 1))
                on_map   = " 🗺️" if cat in VALID_CATS else ""
                db_lines.append(f"  {cat:<28} {cnt:>4}  ({pct:>2}%) {bar}{on_map}")
            db_lines.append(f"{'─'*55}\n")
            logger.info("\n".join(db_lines))
        except Exception as sexc:
            logger.warning(f"⚠️  DB özeti alınamadı: {repr(sexc)}")

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
    """Launch all (or a subset of) spiders gracefully via parallel subprocesses."""
    if is_running():
        logger.warning("⚠️  Scrape zaten çalışıyor – tekrar tetikleme yoksayıldı.")
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
