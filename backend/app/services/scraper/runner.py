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
    """
    Run a single spider in a thread via subprocess.run.
    Using asyncio.to_thread instead of asyncio.create_subprocess_exec because
    the latter raises NotImplementedError on Windows with SelectorEventLoop.
    """
    import sys
    import os
    import subprocess

    t0 = time.monotonic()
    logger.info(f"🕷️  [{name}] → başladı")

    # Full env (includes PATH etc.) + override PYTHONPATH
    env = {**os.environ, "PYTHONPATH": str(repo_root / "backend")}

    def _run() -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(script_path), name],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
        )

    result = await asyncio.to_thread(_run)
    elapsed = time.monotonic() - t0

    if result.returncode == 0:
        logger.info(f"✅ [{name}] → tamamlandı ({elapsed:.0f}s / {elapsed/60:.1f}dk)")
        # Anti-bot uyarılarını topla ve tek özetde bas (log spam önleme)
        stderr_text = result.stderr.decode(errors="replace")
        antibot_lines: list[str] = []
        http403_lines: list[str] = []
        for line in stderr_text.splitlines():
            if any(x in line for x in ["[ANTI-BOT DETECTED", "[BLOCKED", "[POTENTIAL BLOCK"]):
                # URL'yi satırdan çıkar
                url_part = line.split("→")[-1].strip() if "→" in line else line.strip()
                antibot_lines.append(url_part)
            elif "[HTTP 403]" in line or "[NETWORK ERROR]" in line:
                url_part = line.split("→")[-1].strip() if "→" in line else line.strip()
                http403_lines.append(url_part)
        if antibot_lines:
            first = antibot_lines[0][:80]
            last  = antibot_lines[-1][:80] if len(antibot_lines) > 1 else None
            summary = f"🛑 [{name}] {len(antibot_lines)} URL anti-bot tarafından engellendi"
            if last:
                summary += f"\n    İlk: {first}\n    Son:  {last}"
            else:
                summary += f"\n    URL: {first}"
            logger.warning(summary)
        if http403_lines:
            logger.warning(f"🔒 [{name}] {len(http403_lines)} URL HTTP 403 aldı")
    else:
        err = result.stderr.decode(errors="replace")[-500:]
        logger.error(f"💥 [{name}] → HATA ({elapsed:.0f}s)\n{err}")

    return name, result.returncode, elapsed


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
            import os, subprocess
            geocode_script = repo_root / "scripts" / "run_geocode.py"
            geo_env = {**os.environ, "PYTHONPATH": str(repo_root / "backend")}

            def _run_geocode():
                return subprocess.run(
                    [sys.executable, str(geocode_script)],
                    cwd=str(repo_root),
                    env=geo_env,
                    capture_output=True,
                )

            gresult = await asyncio.to_thread(_run_geocode)
            if gresult.returncode == 0:
                logger.info(f"🗺️  Geocoding tamamlandı:\n{gresult.stdout.decode(errors='replace')}")
            else:
                logger.warning(f"⚠️  Geocoding hata:\n{gresult.stderr.decode(errors='replace')[-500:]}")
        except Exception as gexc:
            logger.warning(f"⚠️  Geocoding başlatılamadı: {repr(gexc)}")

        # ── 5. Deduplication ──────────────────────────────────────────────────
        logger.info("🔗 Deduplication başlatılıyor – embedding tabanlı benzerlik analizi...")
        try:
            from app.services.nlp.deduplicator import run_deduplication  # noqa: PLC0415
            dedup_summary = await asyncio.to_thread(run_deduplication)
            logger.info(
                f"🔗 Deduplication tamamlandı: "
                f"toplam={dedup_summary['total']}, "
                f"embedding={dedup_summary['embedded']}, "
                f"eşleşen_çift={dedup_summary['grouped']}, "
                f"güncellenen={dedup_summary['updated']}"
            )
        except Exception as dexc:
            logger.warning(f"⚠️  Deduplication başlatılamadı: {repr(dexc)}")

        # ── 6. DB Özeti ───────────────────────────────────────────────────────
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
            with_hood     = col.count_documents({"neighborhood": {"$ne": None, "$exists": True}})
            coords_no_date = col.count_documents({"coordinates": {"$ne": None}, "published_at": None})
            # Dedup istatistikleri
            unique_groups = len(col.distinct("similarity_group_id", {"similarity_group_id": {"$ne": None}}))
            total_grouped = col.count_documents({"similarity_group_id": {"$ne": None}})
            duplicate_count = total_grouped - unique_groups  # tekrar sayılan haberler
            # Birden fazla ÜYEsi olan gruplar (gerçek duplicate'ler)
            multi_grp_pipeline = [
                {"$match": {"similarity_group_id": {"$ne": None}}},
                {"$group": {"_id": "$similarity_group_id", "cnt": {"$sum": 1}, "srcs": {"$addToSet": "$source"}}},
                {"$match": {"cnt": {"$gt": 1}}},
            ]
            multi_grps = list(col.aggregate(multi_grp_pipeline))
            multi_src_grps = sum(1 for g in multi_grps if len(g["srcs"]) > 1)  # farklı sitelerden gelen
            cat_counts    = list(col.aggregate([
                {"$group": {
                    "_id": "$type",
                    "count": {"$sum": 1},
                    "with_coords": {"$sum": {"$cond": [{"$ne": ["$coordinates", None]}, 1, 0]}}
                }},
                {"$sort": {"count": -1}},
            ]))
            src_counts    = list(col.aggregate([
                {"$group": {"_id": "$source", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]))

            # Mahalleli haberleri al (log için)
            hood_docs = list(col.find(
                {"neighborhood": {"$ne": None, "$exists": True}},
                {"title": 1, "district": 1, "neighborhood": 1, "coordinates": 1}
            ))
            cli.close()

            db_lines = [f"\n── DB Summary {'─'*48}"]
            db_lines.append(f"  Toplam haber           : {total}")
            db_lines.append(f"  Koordinatlı            : {with_coords}  ({100*with_coords//total if total else 0}%)")
            db_lines.append(f"    ├─ Tarihi olan        : {with_coords - coords_no_date}  ← frontenda görünür")
            db_lines.append(f"    └─ Tarihi YOK         : {coords_no_date}  ← frontenda görünmez (tarih filtresi)")
            db_lines.append(f"  Koordinatsız           : {total - with_coords}")
            db_lines.append(f"  Mahalle tespiti        : {with_hood}")
            db_lines.append(f"  {'─'*48}")
            db_lines.append(f"  Dedup – birleştirilen  : {duplicate_count} tekrar haber ({len(multi_grps)} grup)")
            db_lines.append(f"    ├─ Farklı sitelerden  : {multi_src_grps} grup  ← ekranda çoklu kaynak")
            db_lines.append(f"    └─ Aynı siteden       : {len(multi_grps) - multi_src_grps} grup  (aynı URL farklı format)")
            db_lines.append(f"  {'─'*48}")
            db_lines.append(f"  {'Kaynak (Site)':<24} {'Toplam':>8}")
            db_lines.append(f"  {'─'*48}")
            for row in src_counts:
                db_lines.append(f"  {(row['_id'] or '?'):<24} {row['count']:>8}")
            db_lines.append(f"  {'─'*48}")
            db_lines.append(f"  {'Kategori':<28} {'Toplam':>6}  {'Koordinatlı':>11}")
            db_lines.append(f"  {'─'*48}")
            for row in cat_counts:
                cat    = row["_id"] or "Bilinmiyor"
                cnt    = row["count"]
                coords = row["with_coords"]
                db_lines.append(f"  {cat:<28} {cnt:>6}  {coords:>11}")
            if hood_docs:
                db_lines.append(f"  {'─'*48}")
                db_lines.append(f"  Mahalle hassasiyetli koordinatlı haberler:")
                for d in hood_docs:
                    has_coord = "✅" if d.get("coordinates") else "❌"
                    dist = str(d.get("district") or "-")
                    hood = str(d.get("neighborhood") or "-")
                    title = str(d.get("title") or "")[:55]
                    db_lines.append(f"    {has_coord} {dist} / {hood} → {title}")
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
