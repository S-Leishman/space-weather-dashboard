# FINAL REVIEW — Aevion SpaceOps submission candidate

Status: **SUBMISSION_CANDIDATE_READY**

## Repository

| Field | Value |
|---|---|
| URL | https://github.com/S-Leishman/space-weather-dashboard |
| Visibility | PUBLIC |
| Default branch | `main` |
| Release commit SHA | `33c0bbf70e365c986612e69cca300e7b96dc2028` |
| README renders publicly | Yes — HTTP 200 unauthenticated, title and `Known Limitations` present |

Note: the release commit above is the pushed release candidate. This review file and
`IBM-SUBMISSION-CANDIDATE.json` are committed on top of it as the review addendum.

## Test suite

| Field | Value |
|---|---|
| Command | `python -m pytest -q` (isolated `--basetemp`) |
| Collected tests | 140 |
| Exit code | **0** |

Per-file counts: `test_crosspage_coherence.py` 17, `test_crosspage_coherence_guards.py` 16,
`test_dashboard_utils.py` 9, `test_donki_replay.py` 23, `test_evidence_positioning.py` 12,
`test_features.py` 7, `test_frontend.py` 30, `test_ingestion.py` 6, `test_model.py` 7,
`test_p0_regressions.py` 13.

## Five-page browser verification

Fresh detached Streamlit instance on `127.0.0.1:8505`; page URLs discovered from the live
sidebar rather than guessed, because guessing emoji-prefixed page slugs previously served
the wrong page and made About look like the Explorer.

| Page | Render | Raw JS | Exception | Screenshot |
|---|---|---|---|---|
| Home | OK (3986 chars) | none | no | `04_EVIDENCE/lanes/ibm-p0-correctness-001/BROWSER/home.png` |
| Data Pipeline | OK (1321 chars) | none | no | `.../BROWSER/data_pipeline.png` |
| Model Lab | OK (2107 chars) | none | no | `.../BROWSER/model_lab.png` |
| Prediction Explorer | OK (2058 chars) | none | no | `.../BROWSER/prediction_explorer.png` |
| About | OK (5121 chars) | none | no | `.../BROWSER/about.png` |

Assertion results (all PASS):

| Assertion | Result | Evidence |
|---|---|---|
| A — model identity global | PASS | Home `logistic_regression` == Explorer `logistic_regression` == validation champion `logistic_regression` |
| B — artifact root coherence | PASS | Home and Pipeline show the same `features_v1.parquet` SHA-256 `223c8518…059f`; identical artifact root; the 6 missing raw-ingest files are explained in-page, not suppressed |
| C — SHAP claim coherence | PASS | Explorer reports SHAP UNAVAILABLE; About's only SHAP mention is under `FUTURE — NOT OPERATIONALLY QUALIFIED` |
| D — claim ceilings | PASS | zero banned claim strings; maturity levels `IMPLEMENTED` / `PROTOTYPE` / `NOT OPERATIONALLY QUALIFIED` all present |
| E — relabelling | PASS | "Launch Probability" and "p(GO)" absent; "Prototype model score" shown |
| Positioning | PASS | product name, full decision chain, policy state, and human-authority statement all rendered |
| Integrity | PASS | no raw JS, no exceptions, synthetic disclaimer visible, Model Lab candour intact, no fabricated metrics |

Raw record: `04_EVIDENCE/lanes/ibm-p0-correctness-001/BROWSER/BROWSER_VERIFICATION.json`

## Artifact hashes (SHA-256)

| Artifact | SHA-256 | Bytes |
|---|---|---|
| `dashboard/models/logistic_regression.joblib` | `455274f4ee0313bcd65ddb3857e38384b35dd4c021a7d729dbb604be1956c8f3` | 1809 |
| `dashboard/models/logistic_regression_metadata.json` | `8a845f1bf7c3c711b51b5ad9c42f16239596708830ae3c40da494f19dea76289` | 892 |
| `dashboard/models/random_forest.joblib` | `9f3611e9db63d158a34c1292d3cb2696bf582f7336d732ff1fee55816d116b85` | 225737 |
| `dashboard/models/random_forest_metadata.json` | `1215e6231a28b4d630f6f272f95f2c5c9b7f4d41e9f9b85721d282048d2cb72a` | 932 |
| `dashboard/models/xgboost.joblib` | `19edd364420c595e2234911273180a7c19a568dc461053cf1d4f80d33625e65b` | 50419 |
| `dashboard/models/xgboost_metadata.json` | `a6c157b162372665d69d538cdb88433e9f7d65eb377faae311c45e85916cbb07` | 806 |
| `dashboard/models/metrics_summary.json` | `a9b27c2a9d09e7958730d52d63069560a4c1cc9446797d4b26ea094a6b204a37` | 2345 |
| `dashboard/data/processed/features_v1.parquet` | `223c8518985b13e35ba47b522557f15de205e0d9e29e8888d1178a64c768059f` | 62930 |
| `dashboard/data/processed/daily_master.parquet` | `2b2bd93a4fa86dcee167af67dd4d68af2992e5602ee8eb487ab56f80035d0bac` | 20409 |
| `dashboard/data/processed/FEATURE_PROVENANCE.json` | `39f77688771750ae2331f34bb10e46951e4de22fb068cbb5475d6208701e1374` | 1783 |

## Secret / PII scan

**`NO_FINDING`** — 61 files considered, 48 text files scanned, 0 blocking, 0 review.

Scanned for API keys, tokens, credentials, private keys, ASU student/employee and ASURITE
identifiers, personal records, and absolute paths leaking personal directories. Five
absolute-path leaks found in internal markdown on an earlier pass were redacted to
`<REPO_ROOT>` / `<HOME>` and the scan re-run clean. No student credential is published.

Report: `04_EVIDENCE/lanes/ibm-p0-correctness-001/SECRET_SCAN.json`

## README section checklist

| Section | Present |
|---|---|
| `# Aevion SpaceOps` | ✅ |
| Problem Statement | ✅ |
| Solution | ✅ |
| Working Demo | ✅ |
| AI Approach | ✅ |
| System Architecture | ✅ |
| Evidence and Provenance | ✅ |
| Human Authority and Safety Boundary | ✅ |
| Challenge Theme | ✅ |
| How IBM Bob Was Used | ✅ (scoped to what git history and Bob session artifacts support) |
| Data Sources | ✅ |
| Running Locally | ✅ |
| Verification / Tests | ✅ |
| Known Limitations | ✅ (states the label is SYNTHETIC and independent of the features, that there is NO demonstrated predictive skill, and that AUC near 0.5 is expected) |
| Research Experiments | ✅ (quantum claim limited to the approved sentence pair; no advantage claimed) |

No racing language anywhere in the README.

## Video shot list

`docs/VIDEO_SHOT_LIST.md` — ≤3 minutes, bound to the release commit, with exact narration
and screen actions per beat. Screenshots captured for every beat:

| Beat | Screenshot |
|---|---|
| 0:00–0:20 problem | `docs/demo/beat1_problem.png` |
| 0:20–0:40 product | `docs/demo/beat2_product.png` |
| 0:40–1:35 live scenario | `docs/demo/beat3a_inputs.png`, `beat3b_verdict.png`, `beat3c_receipt.png` |
| 1:35–2:15 evidence view | `docs/demo/beat4a_pipeline.png`, `beat4b_provenance.png` |
| 2:15–2:40 IBM Bob usage | `docs/demo/beat5_bob.png` |
| 2:40–3:00 impact | `docs/demo/beat6_impact.png` |

Screen recording is the owner's step: no screen-capture/encoding tooling is available in
this environment, so the storyboard plus per-beat screenshots are the deliverable.

## Remaining owner actions

1. Create and **PUBLISH** the project entry on the BeMyApp platform — a saved draft is not an entry.
2. Complete the IBM SkillsBuild IBM Bob learning activity (each team member must).
3. Record the video from `docs/VIDEO_SHOT_LIST.md`, upload it to a public URL, and confirm it plays while logged out.
4. Press **Publish** before 10:59 PM Central, Aug 31 2026.
