# Aevion SpaceOps

**AI mission-risk decisions with evidence, provenance, and human authority.**

Space weather changes fast, and an operator deciding whether to proceed with a launch
window needs more than a number. Aevion SpaceOps ingests NASA and NOAA space-weather
telemetry, runs a risk model over it, and then does the part most tools skip: it packages
the evidence behind that assessment — model identity, input provenance, timestamps, and a
computed execution receipt — and hands a human a `PASS` / `FAIL` / `UNKNOWN` / `HOLD`
state they can inspect.

The model is an **input**. The product is the **decision record**.

```
SPACE DATA → MODEL INFERENCE → EVIDENCE PACKAGE → PROVENANCE → POLICY CHECK → HUMAN MISSION DECISION
```

Explicitly not: `space data → AI prediction → dashboard`.

---

## Problem Statement

Space weather — solar flares, coronal mass ejections, geomagnetic storms, solar energetic
particle events — threatens launch vehicles, avionics, spacecraft electronics, and crew.
Most launch-support tooling treats terrestrial meteorology as the primary environmental
constraint and handles space weather qualitatively, if at all.

But the deeper problem is not the absence of a prediction. Predictions are cheap now. The
problem is that **a prediction alone does not tell an operator whether it is safe to act
on it.** Confronted with a number on a screen, the person who carries the consequences
cannot answer the questions that actually gate a go/no-go call:

- Which model produced this, at which version, from which inputs?
- How old is the underlying telemetry, and did every source respond?
- Can this exact assessment be reproduced tomorrow, in a review, after an anomaly?
- Where does the software's authority stop and mine begin?

An unauditable recommendation is not decision support. It is a number with a confident
font. In a domain where decisions are reviewed after the fact — and where the reviewer
asks *what did you know and when* — a system that cannot reconstruct its own reasoning has
failed at the moment it mattered most.

## Solution

Aevion SpaceOps is an **evidence-gated mission decision system**.

It runs the pipeline — ingestion, feature engineering, a trained classifier — and then
wraps every inference in a decision record containing:

1. **Model identity** — which model, and the SHA-256 of the serialized artifact.
2. **Input provenance** — source, the input vector, and the fetch/evaluation timestamp.
3. **The score itself** — the prototype model score that produced the state.
4. **A policy state** — `PASS` / `FAIL` / `UNKNOWN` / `HOLD`, with the reasons that
   produced it.
5. **An execution receipt** — the SHA-256 computed over the evidence package itself, so
   it is verifiable by recomputation.
6. **A verification status** — `VERIFIED` only when artifacts and a score are both
   present; otherwise `UNVERIFIED`, never a fabricated pass.

Two rules are enforced in code rather than left to each page
([`dashboard/components/evidence.py`](dashboard/components/evidence.py)):

- **A model score alone never produces `PASS`.** Without verified artifacts the outcome is
  `HOLD`; with no score at all it is `UNKNOWN`. That is what "evidence-gated" means
  operationally.
- **A receipt hash is only ever emitted by actually hashing the package.** There is no code
  path that displays a hash that was not computed, and a test fails the build if a
  64-hex literal appears in any UI source file.

The software never launches, aborts, or authorizes anything. A human does.

## Working Demo

- **Live application:** `streamlit run dashboard/app.py` → `http://localhost:8501`
- **Recorded walkthrough (≤3 min):** *(owner action — see `docs/VIDEO_SHOT_LIST.md`)*
- **Source:** https://github.com/S-Leishman/space-weather-dashboard

Five pages: **Mission Control** (conditions, scenario modelling, mission decision),
**Data Pipeline** (ingestion status and provenance), **Model Lab** (training and metrics),
**Prediction Explorer** (per-prediction scenario exploration and evidence), **About**
(IBM Bob phase log, challenge fit, data sources).

Verified rendering: all five pages render under headless Chromium with no raw-JS leakage,
no page exceptions, and no fabricated metrics. The Mission Control surface has been
captured showing a live `POLICY CHECK: PASS` state with the model identity, the decision
chain, and the evidence package alongside it.

## AI Approach

- **Task.** Binary classification of a launch window as go / no-go from space-weather state.
- **Features.** Rolling Kp averages, lag features, a CME arrival score derived from CME
  speed and half-angle, F10.7 solar flux, storm level, flare occurrence flags in a
  preceding 72-hour window, and cyclical (sin/cos) encodings of launch hour and season.
- **Models.** Logistic Regression, Random Forest, and XGBoost, each fit with `GridSearchCV`
  under stratified cross-validation, with the full metric set persisted per model and each
  `.joblib` accompanied by a metadata JSON carrying the artifact's SHA-256.
- **Model selection.** The model the UI serves is resolved from `metrics_summary.json`'s
  recorded `best_model`, not from a per-page preference order. Every page that shows a
  score resolves identity through one shared loader, so Home, the Prediction Explorer, and
  the recorded validation champion cannot disagree. The current champion is
  **logistic_regression**.
- **Explainability — stated honestly.** SHAP is **not available** in this build: the `shap`
  package is not installed, and no supported explainer can be constructed for the loaded
  estimator. The UI therefore reports *"SHAP explanation UNAVAILABLE"* with the reason and
  shows **no attribution values at all**. Feature importance is displayed only when it can
  be read from the fitted model; otherwise it reports `UNAVAILABLE`. A plausible-looking
  attribution that was never computed from the model is the most misleading artefact this
  kind of product can ship, so this build declines to produce one.
- **A correctness detail worth naming.** The trainer resolves the positive-class column of
  `predict_proba` from the fitted estimator's `classes_` rather than assuming index 1.
  Assuming index 1 is a common silent bug that inverts probabilities whenever class order
  differs. This is exactly the kind of defect an evidence-gated system exists to catch.
- **Refused metrics.** ROC-AUC is **refused** (returned as `null` with a stated reason)
  when the validation split contains only one class, or fewer than two of either class, or
  when the model returns a constant probability. A number is not published where a number
  would be meaningless.

**Read `## Known Limitations` before interpreting any metric on the Model Lab page.** The
modelling machinery is real and correct; the training label is not.

## System Architecture

```
   NASA DONKI ┐
   NOAA SWPC  ├─►  ingestion.py ──►  raw archive + SHA-256 ingest manifest
   NOAA Solar ┘    (retry/backoff,
   Cycle            429 handling)
                          │
                          ▼
                    features.py ──►  FEATURE_PROVENANCE.json
                 (rolling, lag, CME arrival score,
                  cyclical time encoding)
                          │
                          ▼
                 model_trainer.py ──►  *.joblib + *_metadata.json (SHA-256)
                 (LR / RF / XGBoost,               + metrics_summary.json
                  GridSearchCV, stratified CV)
                          │
                          ▼
                     utils.py ──►  feature vector + shared model resolver
                          │
                          ▼
            ┌─────────────────────────────┐
            │  EVIDENCE PACKAGE           │  model id + artifact hash
            │  (components/evidence.py)   │  input provenance + timestamp
            │                             │  score + policy reasons
            │                             │  receipt = SHA-256 of the package
            └──────────────┬──────────────┘
                           ▼
                     POLICY CHECK
                           │
                           ▼
        MISSION STATE:  PASS / FAIL / UNKNOWN / HOLD
                           │
                           ▼
              ►►  HUMAN MISSION DECISION  ◄◄
```

Streamlit multi-page frontend (`dashboard/app.py` + `pages/1–4`), component layer under
`dashboard/components/`, pytest suite under `tests/`, GitHub Actions CI.

## Evidence and Provenance

Every stage emits evidence, and the evidence is addressable rather than decorative:

| Stage | Evidence emitted |
|---|---|
| Ingestion | Raw payload archived; SHA-256 ingest manifest; source URL and fetch timestamp |
| Feature engineering | `FEATURE_PROVENANCE.json` recording filename, SHA-256, row/feature counts, and label semantics |
| Training | Per-model metadata JSON carrying the SHA-256 of its own `.joblib`, plus the full metric set (with refusals recorded as such) |
| Inference | Input vector, model identity, artifact hash, score, policy reasons, timestamp |
| Receipt | SHA-256 computed over the evidence package, verifiable by recomputation |
| Verification | `VERIFIED` only with artifacts *and* a score; otherwise `UNVERIFIED` |

The design rule throughout: **absence of evidence produces `UNKNOWN`, not a default
`PASS`.** A system that degrades toward "looks fine" under missing data is worse than no
system, because it launders uncertainty into confidence.

**Artifact scope, stated plainly.** The processed feature artifact
(`dashboard/data/processed/features_v1.parquet`) and its provenance record are committed.
The **raw** NASA DONKI / NOAA SWPC pulls are **not** committed, so the Data Pipeline page
reports them as `MISSING`. That warning is real and is deliberately not suppressed; run
notebook 01 with a NASA API key to populate them. Both pages resolve the same artifact
root (`dashboard/data/`), and the Data Pipeline page states this explicitly so the two
readings cannot be mistaken for a contradiction.

## Human Authority and Safety Boundary

Stated as a boundary, not a disclaimer:

- The software **does not** launch, abort, authorize, schedule, or command anything.
- It emits a **state** — `PASS` / `FAIL` / `UNKNOWN` / `HOLD` — and the evidence that
  produced it.
- A `HOLD` is a request for a human, not a decision.
- Every consequential action is taken by a person, who is given a record they can inspect
  rather than being asked to trust a number.

**AI recommends. Human authority decides.** The evidence chain exists so that the human is
deciding with more information than the model had, not less.

## Challenge Theme: Advance Space Exploration with AI

Space operations are a domain where AI is genuinely useful and where unaccountable AI is
genuinely dangerous. The same properties that make space-weather risk a good ML target —
continuous multi-source telemetry, real physical consequence — also make it a domain where
"the model said so" is not an acceptable answer in a post-flight review.

This entry advances space exploration by making AI **admissible** in mission decision
loops: not by producing a better number, but by making the number's basis inspectable,
reproducible, and clearly subordinate to human authority. The architecture is
domain-portable — swap the ingestion adapters and the same evidence spine serves satellite
operations, CubeSat scheduling, EVA planning, or ground-system anomaly response.

## How IBM Bob Was Used

IBM Bob was the primary development tool for this application. The project was built in Bob
across seven phases — repository scaffolding; the NASA DONKI / NOAA SWPC ingestion client
with retry and backoff; the feature-engineering layer; the model-training layer; the
Streamlit dashboard; the test suite and CI workflow; and the multi-page frontend and design
system. Every phase is logged on the in-app **About** page, and the corresponding source
files carry per-file Bob attribution headers.

We can evidence that session rather than only assert it. The IBM Bob client workspace
database on the build host records this project in scope throughout the August 30, 2026
session, with the workspace-scoped session log directory created that day and the
application's own paths — `dashboard/app.py`, the component modules, the notebooks, the
test package — present in the session record.

**What Bob did not do, stated plainly.** After the Bob build session closed, an independent
correctness pass was run with separate tooling: cross-page model-identity incoherence was
resolved, fabricated demo metrics and synthetic SHAP/feature-importance values were
removed, ROC-AUC refusal was added for degenerate validation splits, the test suite was
isolated from bundled model artifacts, the evidence/policy layer was added, models were
retrained, and release infrastructure (licence, `.gitignore`, secret-scan record, runtime
pin) was created. That work is not Bob's and is not presented as Bob's.

**An honesty note on provenance.** The application was developed outside version control and
only placed in a repository at release time, so no commit history attributes individual
files. The evidence for Bob's authorship is the session record, the phase log, and per-file
attribution headers — strong at the project level. We decline to convert it into a per-file
forensic claim it cannot support. Stating the boundary of the evidence is the same
discipline this product sells.

## Data Sources

| Source | Content | Licence |
|---|---|---|
| [NASA DONKI](https://kauai.ccmc.gsfc.nasa.gov/DONKI/) | Solar flares, CMEs, geomagnetic storms, SEP events | Public / no restriction |
| [NOAA SWPC planetary K-index (1-min)](https://services.swpc.noaa.gov/json/planetary_k_index_1m.json) | Real-time geomagnetic Kp stream | Public domain |
| [NOAA observed solar-cycle indices](https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json) | Historical F10.7 solar flux | Public domain |

NASA's `DEMO_KEY` works without registration, so the demo runs with no credential. Supply
your own key via the `NASA_API_KEY` environment variable for higher rate limits. **No API
key, token, or personal identifier is committed to this repository.**

## Running Locally

```bash
git clone https://github.com/S-Leishman/space-weather-dashboard.git
cd space-weather-dashboard

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# optional — DEMO_KEY is used if unset
export NASA_API_KEY=your_key_here

streamlit run dashboard/app.py   # http://localhost:8501
```

Python 3.11 (see `runtime.txt`). Pure pip stack, no paid infrastructure, no GPU, no
container required.

## Verification / Tests

```bash
pytest -q
```

- **124 tests, exit code 0**, across nine modules covering ingestion, DONKI replay, feature
  engineering, model behaviour, dashboard utilities, rendered frontend markup (including
  `aria-label` accessibility attributes), cross-page coherence, the evidence/policy layer,
  and P0 regression contracts.
- **Cross-page coherence is tested, not assumed.** A dedicated suite asserts that no page
  hardcodes its own model preference order, that every page resolves the same artifact
  root, that SHAP claims agree across Home, the Prediction Explorer, and About, and that
  the GO score is labelled as a prototype score everywhere.
- **Artifact isolation.** Training under pytest is redirected to a throwaway directory, and
  any test-time write into the packaged `dashboard/models/` raises `ArtifactIsolationError`
  before a single byte changes. This defect was real: a test run silently overwrote shipped
  model artifacts, and the guard exists because of it.
- **Browser verification:** all five pages rendered under headless Chromium — model
  identity coherent across pages, artifact state coherent, SHAP claims matching the
  implementation, no fabricated metrics, no fabricated feature importance, no raw-JS
  leakage, and the synthetic/non-operational disclaimer visible.
- **CI:** GitHub Actions workflow at `.github/workflows/ci.yml` runs the suite on push.

## Known Limitations

**Read this section before reading any metric this project reports.**

- **The training label is SYNTHETIC and is independent of the space-weather features.** The
  go/no-go target the shipped models were fit against was generated from test fixtures. It
  is not derived from historical launch outcomes and carries no relationship to the input
  telemetry.
- **The model therefore has NO demonstrated predictive skill.** None. Not "limited"; none
  has been demonstrated.
- **AUC near 0.5 is the EXPECTED result, not a defect.** A label independent of the
  features cannot be learned from the features. A model reporting strong discrimination on
  this data would be evidence of leakage or of an error in the evaluation — it would be the
  alarming outcome, not the good one. The shipped champion reports ROC-AUC ≈ 0.56, which is
  the expected neighbourhood of chance.
- The bundled `metrics_summary.json` and every figure on the Model Lab page must be read as
  **pipeline-correctness evidence, not predictive-performance evidence.** They demonstrate
  that training, cross-validation, serialization, hashing, and refusal logic execute
  correctly end to end.
- **SHAP is unavailable in this build** and no attribution values are shown anywhere. See
  *AI Approach*.
- The **raw** DONKI/SWPC pulls are not committed, so the Data Pipeline page reports them
  `MISSING` until notebook 01 is run.
- **F10.7 features are derived from a monthly-cadence source.** `ingestion.py` fetches
  NOAA's observed solar-cycle indices, which publish at monthly resolution, while the
  feature builder derives `flux_3d_avg` and `flux_7d_avg` from that series. Those columns
  therefore do not represent true 3-day or 7-day radio-flux variability and must not be
  read as high-frequency operational measurements. A higher-cadence NOAA F10.7 product is
  required before they carry their stated meaning.
- **The Prediction Explorer collapses both flux windows onto a single input.** The page
  assigns the one F10.7 slider value to `flux_3d_avg` and `flux_7d_avg` alike, so the two
  features cannot be varied independently in the interactive path.
- **Live dashboard fetches are NASA DONKI.** NOAA SWPC is ingested by the batch data
  pipeline, not by the dashboard's live path. NOAA SWPC is the official U.S. operational
  forecast authority; NASA DONKI publishes preliminary experimental research information.
  Nothing here is an operational forecast.
- The notebooks contain **zero executed code cells**. They document method; they are not
  reproduced analysis and are not presented as such.
- The CI workflow ships with the repository but has limited execution history, the project
  having been developed outside version control until release.
- Real historical launch outcomes with matched space-weather conditions are the missing
  ingredient. Sourcing and labelling that dataset is the first item of future work, and it
  is a data-acquisition problem, not a modelling one.

We are stating this at full strength on purpose. The submitted system's claim is that a
mission decision should be made on inspectable evidence — a claim that would be worthless
if we obscured what our own evidence says about our own model. The pipeline is real, the
evidence chain is real, the human-authority boundary is real. **The predictive skill is not
yet real, and the system reports that honestly rather than hiding it behind a confident
gauge.** A system that tells you when not to trust it is the entire thesis.

## Research Experiments

Exploratory work, outside the submitted system's architecture.

A separate research lane has demonstrated live IBM quantum-hardware access and receipt
capture. Quantum execution is not required for the submitted mission-risk system and no
quantum advantage is claimed.

---

## Author

Scott Leishman — Arizona State University student.

**Project:** Aevion SpaceOps
**Affiliation:** Aevion LLC

The human-factors reasoning behind the evidence-sufficiency, uncertainty-preservation, and
human-authority design choices is recorded in
[docs/HUMAN_FACTORS_SECTION.md](docs/HUMAN_FACTORS_SECTION.md).

---

## Licence

See [LICENSE](LICENSE).
