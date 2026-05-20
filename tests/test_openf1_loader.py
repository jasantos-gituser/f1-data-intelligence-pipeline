import asyncio
import pytest
from unittest.mock import MagicMock
from f1_pipeline.loaders.openf1_loader import fetch_drivers

@pytest.mark.asyncio
async def test_fetch_drivers_live() -> None:
    """Live call to OpenF1 API — requires network access."""
    cfg = MagicMock()
    cfg.openf1_base_url = "https://api.openf1.org/v1"
    cfg.openf1_timeout_seconds = "30"

    result = await fetch_drivers(cfg, session_key=9158, driver_number=1)
    print("\nRecords returned:", len(result))
    for d in result:
        print(d)

    assert isinstance(result, list)
    assert len(result) > 0
