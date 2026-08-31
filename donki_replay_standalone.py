"""Standalone runner for the DONKI replay card — IBM-DONKI-REPLAY-001.

Delivered standalone rather than wired into dashboard/pages/ because the IBM
release lane was actively editing that tree during this build. See
04_EVIDENCE/lanes/ibm-donki-replay-001/INTEGRATION_PATCH_NOTE.md for the
three-line wiring change once that tree is quiet.

    streamlit run donki_replay_standalone.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard.components.donki_replay import render_replay_card  # noqa: E402

st.set_page_config(page_title="DONKI Post-Event Replay", layout="wide")
render_replay_card(st)
