"""IBM-FINISH-TO-REVIEW-001 STEP 2 — positioning and the evidence/policy layer.

The product is an EVIDENCE-GATED MISSION DECISION SYSTEM; the space-weather
model is an input, not the product. These tests pin the decision chain, the
four-state policy outcome, the human-authority boundary, and the rule that a
receipt hash is only ever shown when it was actually computed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = PRODUCT_ROOT / "dashboard"
APP = DASHBOARD / "app.py"
PAGES = sorted((DASHBOARD / "pages").glob("*.py"))

APP_PY = APP.read_text(encoding="utf-8")
# The UI layer is app.py + pages + the shared rendering components; the decision
# chain and the authority notice are rendered from components/evidence.py.
COMPONENTS = sorted((DASHBOARD / "components").glob("*.py"))
ALL_UI = APP_PY + "\n".join(
    p.read_text(encoding="utf-8") for p in list(PAGES) + list(COMPONENTS)
)

ev = pytest.importorskip("dashboard.components.evidence")


# ─── Positioning ──────────────────────────────────────────────────────────────

def test_product_name_and_framing_present_in_ui():
    assert "Aevion SpaceOps" in ALL_UI
    assert "evidence, provenance, and human authority" in ALL_UI


def test_decision_chain_is_visible_in_ui():
    """The chain must be rendered, not merely described in a docstring."""
    for step in ["SPACE DATA", "MODEL INFERENCE", "EVIDENCE PACKAGE",
                 "PROVENANCE", "POLICY CHECK", "HUMAN MISSION DECISION"]:
        assert step in ALL_UI, f"decision chain step missing from UI: {step}"


def test_human_authority_boundary_is_stated():
    low = ALL_UI.lower()
    assert "does not launch" in low
    assert "a human" in low


# ─── Four-state policy outcome ────────────────────────────────────────────────

def test_policy_states_are_the_four_required_states():
    assert set(ev.POLICY_STATES) == {"PASS", "FAIL", "UNKNOWN", "HOLD"}


def test_unknown_when_no_model_score():
    st = ev.policy_check(score=None, artifacts_ok=True)
    assert st["state"] == "UNKNOWN"
    assert st["reasons"], "an UNKNOWN state must carry the reason it is unknown"


def test_hold_when_artifacts_unverified_even_with_a_score():
    """Evidence-gated: a score alone never produces PASS."""
    st = ev.policy_check(score=0.95, artifacts_ok=False)
    assert st["state"] == "HOLD"


def test_pass_and_fail_are_threshold_driven_when_evidence_is_present():
    assert ev.policy_check(score=0.95, artifacts_ok=True)["state"] == "PASS"
    assert ev.policy_check(score=0.05, artifacts_ok=True)["state"] == "FAIL"


def test_every_state_carries_the_evidence_that_produced_it():
    for score, ok in [(None, True), (0.95, False), (0.95, True), (0.05, True)]:
        st = ev.policy_check(score=score, artifacts_ok=ok)
        assert st["state"] in ev.POLICY_STATES
        assert isinstance(st["reasons"], list) and st["reasons"]
        assert "threshold" in st


# ─── Evidence package + receipt ───────────────────────────────────────────────

def test_evidence_package_has_the_required_fields():
    pkg = ev.build_evidence_package(
        inputs={"kp_3d_avg": 2.0}, source="NASA DONKI",
        model_name="logistic_regression", model_sha256="ab" * 32,
        score=0.5, artifacts_ok=True,
    )
    for field in ["inputs", "source", "model", "timestamp",
                  "result", "verification", "receipt_sha256"]:
        assert field in pkg, f"evidence package missing {field}"


def test_receipt_hash_is_really_computed_over_the_package():
    """Never display a receipt hash that was not actually computed."""
    pkg = ev.build_evidence_package(
        inputs={"kp_3d_avg": 2.0}, source="NASA DONKI",
        model_name="logistic_regression", model_sha256="ab" * 32,
        score=0.5, artifacts_ok=True,
    )
    body = {k: v for k, v in pkg.items() if k != "receipt_sha256"}
    expected = hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert pkg["receipt_sha256"] == expected


def test_receipt_is_absent_not_faked_when_model_is_unavailable():
    pkg = ev.build_evidence_package(
        inputs={}, source="NASA DONKI", model_name=None,
        model_sha256=None, score=None, artifacts_ok=False,
    )
    assert pkg["result"]["score"] is None
    assert pkg["verification"] != "VERIFIED"


def test_no_hardcoded_receipt_hash_literal_in_ui():
    """A 64-hex literal in UI source would be a displayed-but-uncomputed hash."""
    import re
    for path in [APP] + PAGES:
        src = path.read_text(encoding="utf-8")
        for m in re.finditer(r"[0-9a-f]{64}", src):
            pytest.fail(f"hardcoded sha256-looking literal in {path.name}: {m.group()[:16]}…")


def test_home_renders_artifact_receipt_banner():
    """Judge-facing provenance strip is visible under the hero, artifact-backed only."""
    assert "render_artifact_receipt_banner" in APP_PY
    low = APP_PY.lower()
    assert "zymkey" not in low
    assert "ml-dsa" not in low
    assert "attestation" not in low
