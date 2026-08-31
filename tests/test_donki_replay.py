"""Tests for the DONKI replay fixture and card — IBM-DONKI-REPLAY-001.

Two things are guarded here:

1. RENDER SAFETY. The card must not reintroduce the known defect where raw
   markup rendered as visible page text. The card is required to contain no
   `unsafe_allow_html` and to emit no raw HTML/CSS/JS string at all.
2. TRUTH STRUCTURE. The fixture's honesty properties — split verdicts, typed
   edges kept distinct, uncertainty preserved per row, the contradicted
   owner-supplied figure, and the unreconciled representation difference — are
   the deliverable. A refactor that quietly flattens any of them is a
   regression, not a cleanup.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dashboard.components import donki_replay

CARD_SOURCE = Path(donki_replay.__file__).read_text(encoding="utf-8")
# Executable body only. The module docstring names the banned API in order to
# document the contract, which must not itself trip the contract check.
CARD_BODY = CARD_SOURCE.split('"""', 2)[2]


@pytest.fixture(scope="module")
def fx() -> dict:
    return donki_replay.load_fixture()


# ─── Render safety ────────────────────────────────────────────────────────────

def test_card_never_uses_unsafe_allow_html():
    assert "unsafe_allow_html" not in CARD_BODY


def test_card_emits_no_raw_markup_tags():
    """No <script>, <style>, or any HTML tag literal can reach the renderer.

    The original defect surfaced because Streamlit strips <script> elements but
    keeps their text content, printing the body as visible page text. The only
    durable guard is to emit no tags at all.
    """
    for banned in ("<script", "<style", "<div", "<span", "<table", "</"):
        assert banned not in CARD_BODY, f"card source emits raw markup: {banned!r}"
    assert not re.search(r"<[a-zA-Z/][^>\n]{0,40}>", CARD_BODY)


def test_card_renders_without_error_and_writes_no_markup(monkeypatch):
    """Drive the card through a recording stub and inspect every emitted string."""
    emitted: list[str] = []

    class _Col:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def __getattr__(self, _name):
            def _fn(*args, **kwargs):
                emitted.extend(str(a) for a in args)
                return _Col()
            return _fn

    class _St(_Col):
        def columns(self, spec, **kw):
            n = spec if isinstance(spec, int) else len(spec)
            return [_Col() for _ in range(n)]
        def container(self, **kw): return _Col()
        def expander(self, *a, **kw):
            emitted.extend(str(x) for x in a)
            return _Col()

    donki_replay.render_replay_card(_St())

    assert emitted, "card rendered nothing"
    for text in emitted:
        assert "<script" not in text
        assert "<style" not in text
        assert not re.search(r"<[a-zA-Z/][^>\n]{0,40}>", text), f"raw tag in output: {text!r}"


def test_provenance_boundary_is_rendered_verbatim():
    for required in ("NASA CCMC DONKI", "Experimental research information", "NOAA SWPC"):
        assert required in json.dumps(donki_replay.load_fixture())


# ─── Verdict presentation ─────────────────────────────────────────────────────

def test_unknown_is_visually_distinct_from_pass_and_fail():
    """UNKNOWN must read as neither success nor failure."""
    style = donki_replay._VERDICT_STYLE
    pass_colour = style["PASS"][0]
    no_colour = style["NO"][0]
    unknown_colour = style["UNKNOWN"][0]
    assert unknown_colour not in (pass_colour, no_colour)
    assert {pass_colour, no_colour, unknown_colour} == {"green", "red", "violet"}
    # Colour is never the only channel.
    icons = {v[1] for v in style.values()}
    assert len(icons) == len(style)


def test_verdict_styles_cover_every_axis(fx):
    for axis in fx["evidence_assessment"]["axes"]:
        assert axis["verdict"] in donki_replay._VERDICT_STYLE


# ─── Truth structure ──────────────────────────────────────────────────────────

def test_headline_verdicts_stay_split(fx):
    assert fx["evidence_assessment"]["headline_verdicts"] == [
        "FORECAST ARRIVAL CONFIRMED",
        "CAUSAL ATTRIBUTION NOT UNIQUE",
    ]


def test_five_axis_verdicts_are_exact(fx):
    got = {a["axis"]: a["verdict"] for a in fx["evidence_assessment"]["axes"]}
    assert got == {
        "Arrival observed": "PASS",
        "Exact responsible CME": "UNKNOWN",
        "Prediction provenance known": "PASS",
        "Official operational forecast": "NO",
        "Human review required": "POLICY-DEPENDENT",
    }


def test_typed_edges_are_not_flattened(fx):
    used = {e["edge_type"] for e in fx["edges"]}
    assert used == {
        "SOURCE_FLARE", "MODEL_INPUT", "DIRECT_LINK",
        "POSSIBLE_CAUSE", "COINCIDENT_DRIVER", "OBSERVED_OUTCOME",
    }
    for banned in ("related_to", "directly_linked", "RELATED_TO"):
        assert banned not in used
    assert used <= set(fx["edge_types"])


def test_all_five_node_types_present(fx):
    assert set(fx["nodes"]) == {"FLR", "CME", "IPS", "HSS", "WSA_ENLIL"}


def test_combined_run_records_two_model_inputs(fx):
    inputs = [e for e in fx["edges"]
              if e["edge_type"] == "MODEL_INPUT" and e["from"] == "WSA-ENLIL/48261/1"]
    assert len(inputs) == 2
    assert {e["to"] for e in inputs} == {
        "2026-08-25T10:38:00-CME-001", "2026-08-25T12:53:00-CME-001",
    }
    run = next(r for r in fx["nodes"]["WSA_ENLIL"] if r["id"] == "WSA-ENLIL/48261/1")
    assert run["cme_input_count"] == 2
    assert run["estimated_shock_arrival_utc"] == "2026-08-28T09:25Z"
    assert run["uncertainty_band"] == "+/- 7.0 h"


def test_speculative_and_leading_edge_are_one_cme_two_analyses(fx):
    runs = {r["id"]: r for r in fx["nodes"]["WSA_ENLIL"]}
    spec, lead = runs["WSA-ENLIL/48251/1"], runs["WSA-ENLIL/48248/1"]
    assert spec["analysis_type"] == "SPECULATIVE_SHOCK_FRONT"
    assert lead["analysis_type"] == "SINGLE_CME_LEADING_EDGE"
    assert spec["cme_inputs"][0]["cmeid"] == lead["cme_inputs"][0]["cmeid"]
    assert spec["cme_inputs"][0]["featureCode"] == "SH"
    assert lead["cme_inputs"][0]["featureCode"] == "LE"
    assert spec["sibling_analysis"] == lead["id"]
    assert lead["sibling_analysis"] == spec["id"]
    assert fx["normalized_forecast_table"]["double_counting_warning"]


def test_every_forecast_row_carries_analysis_type_and_uncertainty(fx):
    for r in fx["normalized_forecast_table"]["rows"]:
        assert r["analysis_type"], r
        assert r["uncertainty_band"], r
        assert r["source_authority"], r
        assert r["model_identity"], r
        assert r["evidence_grade"] in ("PROVEN", "OWNER_SUPPLIED")


def test_signed_errors_match_the_stated_sign_convention(fx):
    observed = datetime(2026, 8, 28, 8, 30, tzinfo=timezone.utc)
    for r in fx["normalized_forecast_table"]["rows"]:
        predicted = datetime.strptime(
            r["predicted_arrival_utc"], "%Y-%m-%dT%H:%MZ"
        ).replace(tzinfo=timezone.utc)
        assert (predicted - observed).total_seconds() / 60 == r["signed_error_minutes"]
        expected_dir = "LATE" if r["signed_error_minutes"] > 0 else "EARLY"
        assert expected_dir in r["signed_error_human"]


def test_rows_are_ranked_by_arrival_time_not_sequence(fx):
    times = [r["predicted_arrival_utc"] for r in fx["normalized_forecast_table"]["rows"]]
    assert times == sorted(times)


def test_owner_supplied_aggregate_is_recorded_as_contradicted(fx):
    c = fx["contradicted_inputs"][0]
    assert c["verdict"] == "CONTRADICTED"
    assert "08:33" in c["owner_supplied_value"]
    assert "09:45" in c["retrieved_value"]


def test_hss_representation_difference_is_not_reconciled(fx):
    d = fx["representation_discrepancies"][0]
    assert d["resolution"] == "NOT_RECONCILED_BY_DESIGN"
    assert d["representation_a"]["hss_present_in_linked_events"] is True
    assert d["representation_b"]["hss_present_in_direct_link_list"] is False
    assert d["representation_a"]["evidence_grade"] == "PROVEN"
    assert d["representation_b"]["evidence_grade"] == "OWNER_SUPPLIED"
    assert d["not_a_criticism"]
    coincident = [e for e in fx["edges"] if e["edge_type"] == "COINCIDENT_DRIVER"]
    assert len(coincident) == 2, "the IPS <-> HSS association must be bidirectional"


def test_forbidden_claims_are_recorded_as_refused(fx):
    refused = " ".join(c["claim"] + c["reason"] for c in fx["refused_claims"])
    assert all(c["status"] == "REFUSED" for c in fx["refused_claims"])
    for topic in ("three minutes", "55-minute", "predicted the event", "official"):
        assert topic in refused


def test_no_precision_claim_anywhere_in_fixture_or_card(fx):
    """A forbidden phrase may appear only where it is being refused.

    The fixture quotes the banned wording verbatim on purpose — a refusal is
    only auditable if it names what was refused. So rather than banning the
    strings outright, require every occurrence to sit next to a refusal marker.
    An unqualified occurrence is the actual regression.
    """
    blob = (json.dumps(fx) + CARD_BODY).lower()
    markers = ("refus", "contradict", "never", "not a", "is not", "must not", "cannot")
    for banned in ("within three minutes", "highly accurate", "proved that",
                   "aevion predicted", "caused by cme"):
        for m in re.finditer(re.escape(banned), blob):
            window = blob[max(0, m.start() - 200):m.end() + 200]
            assert any(k in window for k in markers), (
                f"{banned!r} appears without a nearby refusal marker: ...{window}..."
            )


def test_decision_word_comes_from_implemented_policy(fx):
    from dashboard.components.evidence import POLICY_STATES, policy_check

    pol = fx["implemented_policy_state"]
    assert tuple(pol["available_states"]) == POLICY_STATES
    # No Aevion forecast exists for this event, so there is no score.
    assert policy_check(None, True)["state"] == pol["state_for_this_replay"]


def test_observed_receipt_lists_instruments_and_platforms(fx):
    ips = fx["nodes"]["IPS"][0]
    assert ips["event_time_utc"] == "2026-08-28T08:30Z"
    assert len(ips["detecting_instruments"]) == 6
    assert {i.split(":")[0] for i in ips["detecting_instruments"]} == {"SOLAR-1", "ACE", "IMAP"}


def test_every_source_has_a_retrieval_timestamp(fx):
    assert len(fx["sources"]) >= 8
    for s in fx["sources"]:
        assert s["url"].startswith("https://")
        datetime.strptime(s["retrieved_at_utc"], "%Y-%m-%dT%H:%MZ")


def test_dataframe_is_well_formed(fx):
    df = donki_replay.forecast_dataframe(fx)
    assert len(df) == len(fx["normalized_forecast_table"]["rows"])
    assert list(df.columns) == donki_replay._TABLE_COLUMNS
    assert not df.isnull().any().any()
