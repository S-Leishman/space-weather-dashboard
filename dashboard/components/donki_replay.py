"""DONKI post-event replay card — IBM-DONKI-REPLAY-001.

Renders one replay card for the 2026-08-25 -> 2026-08-28 DONKI event cluster.

RENDER-SAFETY CONTRACT
----------------------
This module contains NO `unsafe_allow_html` and emits no raw HTML string.
Every visual element is a native Streamlit primitive (st.metric, st.dataframe,
st.badge, st.columns, st.container, st.caption). This is deliberate: the
known defect in this app rendered raw JavaScript as visible page text after an
`st.markdown(html, unsafe_allow_html=True)` call. A hand-built HTML card on the
submission page is the most likely way to reintroduce it, so the card forgoes
custom styling entirely. `tests/test_donki_replay.py` asserts this contract.

Verdict states are distinguished by BOTH colour and an icon, so PASS / UNKNOWN /
NO remain separable without relying on colour alone. UNKNOWN renders violet —
neither the green of success nor the red of failure — because the product's
claim is that it refuses to collapse uncertainty into either.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "04_EVIDENCE" / "lanes" / "ibm-donki-replay-001" / "DONKI_REPLAY_FIXTURE.json"
)

# Verdict -> (st.badge colour, leading icon). Colour is semantic, never decorative.
# violet for UNKNOWN is the load-bearing choice: present and legible, but read as
# neither success nor failure.
_VERDICT_STYLE: dict[str, tuple[str, str]] = {
    "PASS":             ("green",  ":material/check_circle:"),
    "UNKNOWN":          ("violet", ":material/help:"),
    "NO":               ("red",    ":material/block:"),
    "POLICY-DEPENDENT": ("blue",   ":material/gavel:"),
}

_TABLE_COLUMNS = [
    "Producer", "Model", "Analysis type", "CME inputs",
    "Predicted (UTC)", "Uncertainty", "Signed error", "Predicted Kp", "Authority",
]


def load_fixture(path: Path | str | None = None) -> dict[str, Any]:
    """Load the frozen replay fixture."""
    return json.loads(Path(path or FIXTURE_PATH).read_text(encoding="utf-8"))


def forecast_dataframe(fixture: dict[str, Any]) -> pd.DataFrame:
    """Normalized forecast table, ranked by predicted arrival time."""
    rows = []
    for r in fixture["normalized_forecast_table"]["rows"]:
        rows.append({
            "Producer": r["producer"],
            "Model": r["model_identity"],
            "Analysis type": r["analysis_type"].replace("_", " ").title(),
            "CME inputs": len(r["cme_inputs"]) if r["cme_input_count"] is not None else "n/a",
            "Predicted (UTC)": r["predicted_arrival_utc"],
            "Uncertainty": r["uncertainty_band"].replace("_", " ").lower(),
            "Signed error": r["signed_error_human"],
            "Predicted Kp": r["predicted_kp"],
            "Authority": r["source_authority"],
        })
    return pd.DataFrame(rows, columns=_TABLE_COLUMNS)


def render_replay_card(st, fixture: dict[str, Any] | None = None) -> None:
    """Render the single DONKI replay card. Native primitives only."""
    fx = fixture or load_fixture()
    table = fx["normalized_forecast_table"]
    ips = fx["nodes"]["IPS"][0]
    pb = fx["provenance_boundary"]

    with st.container(border=True):
        st.subheader("Post-Event Replay — DONKI cluster 2026-08-25 → 2026-08-28")

        # --- Provenance boundary. Close to verbatim, and never optional. -------
        p1, p2, p3 = st.columns(3)
        p1.caption(f"**Source:** {pb['source']}")
        p2.caption(f"**Classification:** {pb['classification']}")
        p3.caption(f"**Operational forecast authority:** {pb['operational_forecast_authority']}")
        st.caption(
            "Aevion produced none of these forecasts. This card preserves third-party "
            "predictions and a later observation; it does not make one."
        )

        st.divider()

        # --- The reduced decision surface -------------------------------------
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Observed shock (IPS)", "2026-08-28 08:30Z",
                  help=f"Detected by {len(ips['detecting_instruments'])} instruments "
                       f"across {ips['detecting_platform_count']} platforms: SOLAR-1, ACE, IMAP.")
        m2.metric("Independent producers", table["independent_producer_count"],
                  help=", ".join(table["independent_producers"]))
        m3.metric("Arrival window across producers", "06:00 – 15:00Z",
                  help="Excludes the speculative shock-front row and the derived "
                       "aggregate. Full span including both: 00:32 – 15:00Z.")
        m4.metric("Attribution", "MULTI-SOURCE",
                  help=ips["attribution_note_verbatim"])

        st.divider()

        # --- The two headline verdicts, deliberately split --------------------
        h1, h2 = st.columns(2)
        with h1:
            st.badge("FORECAST ARRIVAL CONFIRMED", color="green",
                     icon=":material/check_circle:")
        with h2:
            st.badge("CAUSAL ATTRIBUTION NOT UNIQUE", color="violet",
                     icon=":material/help:")

        # --- Per-axis verdicts ------------------------------------------------
        st.caption("EVIDENCE ASSESSMENT")
        axes = fx["evidence_assessment"]["axes"]
        for col, axis in zip(st.columns(len(axes)), axes):
            colour, icon = _VERDICT_STYLE[axis["verdict"]]
            with col:
                st.badge(axis["verdict"], color=colour, icon=icon)
                st.caption(axis["axis"])

        with st.expander("Why each verdict", expanded=False):
            for axis in axes:
                st.markdown(f"**{axis['axis']} — {axis['verdict']}**")
                st.caption(axis["basis"])

        st.divider()

        # --- Normalized forecast table ----------------------------------------
        st.caption("NORMALIZED FORECAST TABLE — model identity, analysis type, "
                   "uncertainty, and source authority preserved per row")
        st.caption(table["sign_convention"])
        st.dataframe(forecast_dataframe(fx), hide_index=True,
                     use_container_width=True)

        st.warning(
            "Two rows are alternative analyses of ONE CME (2026-08-25T10:38Z), "
            "differing only by feature code — leading edge (LE) at 10:41Z and "
            "speculative shock front (SH) at 00:32Z. They are not two producers "
            "disagreeing, and any spread computed over all nine rows double-counts them.",
            icon=":material/warning:",
        )
        st.info(
            "The closest nominal agreement — WSA-ENLIL run 48261 at 09:25Z, +55 min — "
            "is the only run that took TWO CMEs as explicit model inputs. Its published "
            "uncertainty band is ±7 h. A 55-minute nominal difference inside a "
            "14-hour-wide band is agreement, NOT precision.",
            icon=":material/info:",
        )

        st.divider()

        # --- Recorded linkage vs causal confidence ----------------------------
        st.caption("TYPED EDGES — recorded linkage is not causal confidence")
        counts: dict[str, int] = {}
        for e in fx["edges"]:
            counts[e["edge_type"]] = counts.get(e["edge_type"], 0) + 1
        st.dataframe(
            pd.DataFrame(
                [{"Edge type": k, "Count": v, "Meaning": fx["edge_types"][k]}
                 for k, v in counts.items()]
            ),
            hide_index=True, use_container_width=True,
        )

        disc = fx["representation_discrepancies"][0]
        with st.expander(
            "Representation difference preserved — is the high speed stream a linked activity?",
            expanded=False,
        ):
            st.caption(disc["subject"])
            d1, d2 = st.columns(2)
            with d1:
                st.markdown(f"**{disc['representation_a']['name']}**")
                st.badge("HSS PRESENT", color="blue", icon=":material/link:")
                st.caption(f"Evidence grade: {disc['representation_a']['evidence_grade']}")
            with d2:
                st.markdown(f"**{disc['representation_b']['name']}**")
                st.badge("HSS ABSENT", color="orange", icon=":material/link_off:")
                st.caption(f"Evidence grade: {disc['representation_b']['evidence_grade']}")
                st.caption(disc["representation_b"]["verification_limit"])
            st.caption(f"Resolution: {disc['resolution']}")
            st.caption(disc["why_preserved"])
            st.success(disc["not_a_criticism"], icon=":material/science:")

        st.divider()

        # --- Decision state, from the actually implemented policy -------------
        pol = fx["implemented_policy_state"]
        colour, icon = _VERDICT_STYLE.get(pol["state_for_this_replay"], ("violet", ":material/help:"))
        st.caption("MISSION RISK STATE")
        st.badge(f"POLICY CHECK: {pol['state_for_this_replay']}", color=colour, icon=icon)
        st.caption(
            f"State vocabulary is exactly what the implemented policy emits "
            f"({', '.join(pol['available_states'])}), from {pol['vocabulary_source']}. "
            f"{pol['why']}"
        )
        st.caption(pol["human_authority_notice"])

        st.divider()
        st.caption(f"CLAIM CEILING — {fx['claim_ceiling']}")
