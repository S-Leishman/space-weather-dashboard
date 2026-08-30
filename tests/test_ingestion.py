"""
Unit tests for dashboard/components/ingestion.py
IBM Bob generated — Phase 6.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_raw_dir(tmp_path):
    """Temporary data/raw directory."""
    raw = tmp_path / "raw"
    raw.mkdir()
    return raw


@pytest.fixture
def mock_flr_response():
    return [
        {"flrID": "2024-01-15T00:00:00-FLR-001",
         "beginTime": "2024-01-15T00:00Z",
         "classType": "X2.1",
         "sourceLocation": "N25W30"},
        {"flrID": "2024-01-16T12:00:00-FLR-002",
         "beginTime": "2024-01-16T12:00Z",
         "classType": "M5.3",
         "sourceLocation": "S10E05"},
    ]


@pytest.fixture
def mock_empty_response():
    return []


# ─── Happy path ───────────────────────────────────────────────────────────────

def test_fetch_donki_returns_list(tmp_raw_dir, mock_flr_response):
    """fetch_donki saves file and returns a list."""
    with patch("dashboard.components.ingestion.RAW_DIR", tmp_raw_dir), \
         patch("dashboard.components.ingestion._get", return_value=mock_flr_response):
        from dashboard.components.ingestion import fetch_donki
        result = fetch_donki("FLR", "2024-01-01", "2024-01-31", api_key="TEST")
    assert isinstance(result, list)
    assert len(result) == 2
    saved = list(tmp_raw_dir.glob("donki_flr_*.json"))
    assert len(saved) == 1
    loaded = json.loads(saved[0].read_text())
    assert loaded == mock_flr_response


def test_sha256_file_is_deterministic(tmp_raw_dir):
    """sha256_file returns same hex for same content."""
    from dashboard.components.ingestion import sha256_file
    p = tmp_raw_dir / "test.json"
    p.write_bytes(b'{"hello": "world"}')
    h1 = sha256_file(p)
    h2 = sha256_file(p)
    assert h1 == h2
    assert len(h1) == 64


def test_ingest_all_creates_manifest(tmp_raw_dir, mock_flr_response):
    """ingest_all creates ingest_manifest.json with sha256 entries."""
    dummy_data: dict = {"data": [1, 2, 3]}

    with patch("dashboard.components.ingestion.RAW_DIR", tmp_raw_dir), \
         patch("dashboard.components.ingestion._get", return_value=dummy_data), \
         patch("dashboard.components.ingestion.fetch_kp_index", return_value=[]), \
         patch("dashboard.components.ingestion.fetch_solar_flux", return_value=[]):
        from importlib import reload
        import dashboard.components.ingestion as ing
        ing.RAW_DIR = tmp_raw_dir

        # Patch at module level
        with patch.object(ing, "_get", return_value=dummy_data), \
             patch.object(ing, "fetch_kp_index", return_value=[]), \
             patch.object(ing, "fetch_solar_flux", return_value=[]):
            results = ing.ingest_all("2024-01-01", "2024-01-31", api_key="TEST")

    manifest_path = tmp_raw_dir / "ingest_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert "ingested_at" in manifest
    assert "files" in manifest


# ─── Edge case ────────────────────────────────────────────────────────────────

def test_fetch_donki_empty_response(tmp_raw_dir):
    """fetch_donki handles empty API response gracefully."""
    with patch("dashboard.components.ingestion.RAW_DIR", tmp_raw_dir), \
         patch("dashboard.components.ingestion._get", return_value=None):
        from dashboard.components.ingestion import fetch_donki
        result = fetch_donki("CME", "2024-01-01", "2024-01-31", api_key="TEST")
    assert result == []


def test_fetch_donki_unknown_event_type():
    """fetch_donki raises ValueError for unknown event_type."""
    from dashboard.components.ingestion import fetch_donki
    with pytest.raises(ValueError, match="Unknown event_type"):
        fetch_donki("INVALID", "2024-01-01", "2024-01-31")


# ─── Error condition ──────────────────────────────────────────────────────────

def test_get_retries_on_rate_limit(tmp_raw_dir):
    """_get retries on HTTP 429 and eventually raises on exhaustion."""
    import requests
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429
    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = []
    mock_response_200.raise_for_status = MagicMock()

    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return mock_response_429
        return mock_response_200

    with patch("requests.get", side_effect=side_effect), \
         patch("time.sleep"):
        from dashboard.components.ingestion import _get
        result = _get("http://example.com", retries=5, backoff=0.001)
    assert result == []
    assert call_count == 3
