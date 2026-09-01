"""Evidence-gated mission decision layer.

Aevion SpaceOps is a mission-risk decision system. The space-weather model is
an *input* to that system, not the product. This module owns the part of the
product that is actually the product:

    SPACE DATA → MODEL INFERENCE → EVIDENCE PACKAGE → PROVENANCE
                → POLICY CHECK → HUMAN MISSION DECISION

Two rules are enforced here rather than left to each page:

1. A model score alone never produces a PASS. Without verified artifacts the
   outcome is HOLD, and without a score at all it is UNKNOWN. This is what
   "evidence-gated" means operationally.
2. A receipt hash is only ever emitted by actually hashing the evidence
   package. There is no code path that displays a hash that was not computed.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

POLICY_STATES = ("PASS", "FAIL", "UNKNOWN", "HOLD")

# Prototype thresholds. These gate a *prototype score*, not a calibrated
# probability, and are deliberately not tuned — the training label is synthetic.
GO_THRESHOLD = 0.65
NO_GO_THRESHOLD = 0.40

HUMAN_AUTHORITY_NOTICE = (
    "This system does not launch, abort, or authorize anything. It assembles "
    "evidence and applies a policy check; a human holds mission authority and "
    "makes the decision."
)

DECISION_CHAIN = (
    "SPACE DATA",
    "MODEL INFERENCE",
    "EVIDENCE PACKAGE",
    "PROVENANCE",
    "POLICY CHECK",
    "HUMAN MISSION DECISION",
)


def policy_check(score: float | None, artifacts_ok: bool,
                 go_threshold: float = GO_THRESHOLD,
                 no_go_threshold: float = NO_GO_THRESHOLD) -> dict[str, Any]:
    """Four-state policy outcome, always with the evidence that produced it.

    UNKNOWN — no score exists (no model loaded / inference failed).
    HOLD    — a score exists but the supporting artifacts are not verified,
              or the score sits in the indeterminate band.
    FAIL    — verified evidence and a score below the no-go threshold.
    PASS    — verified evidence and a score above the go threshold.
    """
    reasons: list[str] = []
    threshold = {"go": go_threshold, "no_go": no_go_threshold}

    if score is None:
        reasons.append("No model score available — model not loaded or inference failed.")
        reasons.append("Cannot evaluate policy without an inference result.")
        return {"state": "UNKNOWN", "reasons": reasons, "threshold": threshold,
                "score": None}

    if not artifacts_ok:
        reasons.append(f"Prototype model score = {score:.3f}.")
        reasons.append("Supporting artifacts are NOT verified (provenance incomplete).")
        reasons.append("Evidence gate: a score alone cannot produce PASS.")
        return {"state": "HOLD", "reasons": reasons, "threshold": threshold,
                "score": score}

    reasons.append(f"Prototype model score = {score:.3f}.")
    reasons.append("Supporting artifacts verified against the provenance record.")

    if score >= go_threshold:
        state = "PASS"
        reasons.append(f"Score is at or above the go threshold ({go_threshold:.2f}).")
    elif score < no_go_threshold:
        state = "FAIL"
        reasons.append(f"Score is below the no-go threshold ({no_go_threshold:.2f}).")
    else:
        state = "HOLD"
        reasons.append(
            f"Score is in the indeterminate band "
            f"[{no_go_threshold:.2f}, {go_threshold:.2f}) — no automatic call."
        )

    reasons.append(HUMAN_AUTHORITY_NOTICE)
    return {"state": state, "reasons": reasons, "threshold": threshold, "score": score}


def build_evidence_package(inputs: dict, source: str, model_name: str | None,
                           model_sha256: str | None, score: float | None,
                           artifacts_ok: bool,
                           timestamp: str | None = None) -> dict[str, Any]:
    """Assemble the evidence package and hash it into a receipt.

    The receipt is the SHA-256 of the canonical JSON of every other field, so
    it is verifiable by recomputation and cannot be present without the body
    that produced it.
    """
    decision = policy_check(score, artifacts_ok)
    body: dict[str, Any] = {
        "inputs": inputs,
        "source": source,
        "model": {"name": model_name, "sha256": model_sha256},
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "result": {
            "score": score,
            "state": decision["state"],
            "reasons": decision["reasons"],
            "threshold": decision["threshold"],
        },
        "verification": (
            "VERIFIED" if (artifacts_ok and model_sha256 and score is not None)
            else "UNVERIFIED"
        ),
    }
    body["receipt_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode()
    ).hexdigest()
    return body


# ─── Rendering ────────────────────────────────────────────────────────────────

_STATE_COLOR = {
    "PASS": "#00FF41",
    "FAIL": "#FF4444",
    "HOLD": "#FFD700",
    "UNKNOWN": "#8892A4",
}


def render_decision_chain(st, active: str | None = None) -> None:
    """Render the mission decision chain so the pipeline is visible, not implied."""
    cells = []
    for step in DECISION_CHAIN:
        on = (step == active)
        color = "#00D4FF" if on else "#4A5568"
        weight = "600" if on else "400"
        cells.append(
            f'<span style="color:{color};font-weight:{weight};">{step}</span>'
        )
    st.markdown(
        '<div style="font-family:IBM Plex Mono,monospace;font-size:0.6rem;'
        'letter-spacing:0.05em;padding:0.5rem 0;color:#4A5568;">'
        + ' <span style="color:#1C2640;">&#8594;</span> '.join(cells)
        + '</div>',
        unsafe_allow_html=True,
    )


def render_policy_state(st, decision: dict) -> None:
    """Render the PASS / FAIL / UNKNOWN / HOLD state with its evidence."""
    state = decision["state"]
    color = _STATE_COLOR.get(state, "#8892A4")
    st.markdown(
        f'<div style="font-family:Orbitron,IBM Plex Mono,monospace;'
        f'font-size:0.95rem;font-weight:700;color:{color};'
        f'border:1px solid {color};border-radius:4px;padding:0.45rem 0.9rem;'
        f'display:inline-block;letter-spacing:0.08em;">POLICY CHECK: {state}</div>',
        unsafe_allow_html=True,
    )
    for r in decision["reasons"]:
        st.caption(f"• {r}")


def render_artifact_receipt_banner(
    st,
    *,
    model_name: str | None,
    model_sha256: str | None,
    provenance: dict,
    receipt_sha256: str | None = None,
    verification: str | None = None,
) -> None:
    """Judge-facing artifact strip under the hero.

    Only artifact-backed fields already loaded from disk are shown. No hardware
    attestation, HSM, or Zymkey claims — those require a separate qualified lane.
    """
    prov_ok = bool(provenance and "note" not in provenance)
    feat_sha = provenance.get("sha256") if prov_ok else None
    ver = verification or (
        "VERIFIED" if prov_ok and model_sha256 else "UNVERIFIED"
    )

    def trunc(value: str | None) -> str:
        if not value:
            return "UNAVAILABLE"
        return f"{value[:16]}…" if len(value) > 16 else value

    receipt = trunc(receipt_sha256) if receipt_sha256 else "PENDING"
    st.markdown(
        '<div class="swl-receipt-banner" aria-label="Artifact receipt strip">'
        f'<span>MODEL · {model_name or "UNAVAILABLE"}</span>'
        f'<span class="swl-receipt-sep">|</span>'
        f'<span>MODEL SHA · {trunc(model_sha256)}</span>'
        f'<span class="swl-receipt-sep">|</span>'
        f'<span>FEATURES SHA · {trunc(feat_sha)}</span>'
        f'<span class="swl-receipt-sep">|</span>'
        f'<span>VERIFICATION · {ver}</span>'
        f'<span class="swl-receipt-sep">|</span>'
        f'<span>RECEIPT SHA · {receipt}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_evidence_drawer(st, package: dict) -> None:
    """Small, real evidence drawer. Every value shown is a value we computed."""
    state = package["result"]["state"]
    with st.expander(f"EVIDENCE PACKAGE — {state}", expanded=False):
        st.caption(f"SOURCE: {package['source']}")
        st.caption(f"MODEL: {package['model']['name'] or 'UNAVAILABLE'}")
        st.caption(f"MODEL SHA-256: {package['model']['sha256'] or 'UNAVAILABLE'}")
        st.caption(f"TIMESTAMP: {package['timestamp']}")
        score = package["result"]["score"]
        st.caption(
            "PROTOTYPE MODEL SCORE: "
            + (f"{score:.4f}" if score is not None else "UNAVAILABLE")
        )
        st.caption(f"VERIFICATION: {package['verification']}")
        st.caption(f"RECEIPT SHA-256 (computed over this package): {package['receipt_sha256']}")
        st.caption(HUMAN_AUTHORITY_NOTICE)
        st.json(package, expanded=False)
