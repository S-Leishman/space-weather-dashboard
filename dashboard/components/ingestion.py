"""
NASA DONKI + NOAA SWPC data ingestion utilities.
IBM Bob generated — Phase 2.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

BASE_DONKI = "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get"
BASE_SWPC_KP = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
BASE_SWPC_FLUX = "https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json"

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def _get(url: str, params: dict | None = None, retries: int = 5, backoff: float = 1.0) -> Any:
    """GET with exponential back-off retry and rate-limit handling."""
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429:
                wait = backoff * (2 ** attempt)
                print(f"[rate-limit] sleeping {wait:.1f}s …")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as exc:
            if attempt == retries - 1:
                raise
            wait = backoff * (2 ** attempt)
            print(f"[retry {attempt+1}] {exc}  sleeping {wait:.1f}s …")
            time.sleep(wait)


def _save_raw(data: Any, name: str) -> Path:
    dest = RAW_DIR / name
    dest.write_text(json.dumps(data, indent=2, default=str))
    print(f"  saved → {dest}  ({dest.stat().st_size:,} bytes)")
    return dest


def fetch_donki(
    event_type: str,
    start_date: str,
    end_date: str,
    api_key: str = "DEMO_KEY",
) -> list[dict]:
    """
    Fetch a DONKI event stream.
    event_type: FLR | CME | GST | SEP
    Dates: YYYY-MM-DD strings.
    """
    endpoints = {
        "FLR": "/FLR",
        "CME": "/CME",
        "GST": "/GST",
        "SEP": "/SEP",
    }
    if event_type not in endpoints:
        raise ValueError(f"Unknown event_type '{event_type}'. Valid: {list(endpoints)}")

    url = BASE_DONKI + endpoints[event_type]
    params = {
        "startDate": start_date,
        "endDate": end_date,
        "api_key": api_key,
    }
    print(f"[DONKI] fetching {event_type}  {start_date} → {end_date}")
    data = _get(url, params=params)
    if data is None:
        data = []
    name = f"donki_{event_type.lower()}_{start_date}_{end_date}.json"
    _save_raw(data, name)
    return data


def fetch_kp_index() -> list[dict]:
    """Fetch the NOAA real-time 1-minute Kp index stream."""
    print("[SWPC] fetching Kp index …")
    data = _get(BASE_SWPC_KP)
    _save_raw(data, "swpc_kp_1m.json")
    return data


def fetch_solar_flux() -> list[dict]:
    """Fetch the NOAA observed solar cycle indices (includes F10.7)."""
    print("[SWPC] fetching solar flux F10.7 …")
    data = _get(BASE_SWPC_FLUX)
    _save_raw(data, "swpc_solar_cycle_indices.json")
    return data


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def ingest_all(
    start_date: str,
    end_date: str,
    api_key: str = "DEMO_KEY",
) -> dict[str, Path]:
    """Run full ingestion pipeline and return mapping of name → path."""
    results: dict[str, Path] = {}
    for etype in ["FLR", "CME", "GST", "SEP"]:
        data = fetch_donki(etype, start_date, end_date, api_key)
        name = f"donki_{etype.lower()}_{start_date}_{end_date}.json"
        results[etype] = RAW_DIR / name

    results["KP"] = _save_raw(fetch_kp_index(), "swpc_kp_1m.json")
    results["FLUX"] = _save_raw(fetch_solar_flux(), "swpc_solar_cycle_indices.json")

    # Write ingest manifest
    manifest = {
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "files": {k: {"path": str(v), "sha256": sha256_file(v)} for k, v in results.items()},
    }
    manifest_path = RAW_DIR / "ingest_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n[manifest] {manifest_path}")
    return results
