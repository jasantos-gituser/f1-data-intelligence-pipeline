import asyncio
import logging
import httpx
from typing import Any

from f1_pipeline.config import Config

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3

async def fetch_session(
    config: Config,
    session_year: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch session records from OpenF1 API for a given year."""
    params: dict[str, Any] = {"year": session_year}

    url = f"{config.openf1_base_url}/sessions"
    sessions = await _get(config, url, params)

    all_drivers: list[dict[str, Any]] = []
    for session in sessions:
        session_key = session["session_key"]
        drivers = await fetch_drivers(config, session_key)
        all_drivers.extend(drivers)
        await asyncio.sleep(0.25)

    return all_drivers

async def fetch_drivers(
    config: Config,
    session_key: int | str,
    #driver_number: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch driver records from OpenF1 API for a given session."""
    params: dict[str, Any] = {"session_key": session_key}
    #if driver_number is not None:
    #    params["driver_number"] = driver_number

    url = f"{config.openf1_base_url}/drivers"
    return await _get(config, url, params)


async def _get(
    config: Config,
    url: str,
    params: dict[str, Any],
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """GET with exponential-backoff retry. Returns parsed JSON list."""
    request_timeout = timeout or float(config.openf1_timeout_seconds or 30)

    async with httpx.AsyncClient(timeout=request_timeout) as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 404:
                    logger.info("GET %s → 404 no results", url)
                    return []
                resp.raise_for_status()
                result: list[dict[str, Any]] = resp.json()
                logger.info("GET %s → %d records", url, len(result))
                return result
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                if attempt == _MAX_RETRIES:
                    raise RuntimeError(
                        f"OpenF1 request failed after {_MAX_RETRIES} attempts: {exc}"
                    ) from exc
                wait = 2**attempt
                logger.warning(
                    "Attempt %d/%d failed, retrying in %ds: %s",
                    attempt,
                    _MAX_RETRIES,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)

    return []
