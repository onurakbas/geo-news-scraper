"""
Scrape trigger endpoint – POST /api/v1/scrape/trigger
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.services.scraper.runner import get_scrape_state, is_running, run_spiders_background

router = APIRouter()


@router.post("/trigger", summary="Trigger a new scrape run")
async def trigger_scrape(background_tasks: BackgroundTasks) -> dict:
    """
    Launch all spiders in the background.
    Returns 409 if a scrape is already in progress.
    """
    if is_running():
        raise HTTPException(
            status_code=409,
            detail="A scrape is already in progress. Please wait until it finishes.",
        )

    background_tasks.add_task(run_spiders_background)
    return {"status": "started", "message": "Scrape triggered. Check /status for progress."}


@router.get("/status", summary="Get current scrape status")
async def scrape_status() -> dict:
    """Return the current scrape state (idle / running + last run metadata)."""
    return get_scrape_state()
