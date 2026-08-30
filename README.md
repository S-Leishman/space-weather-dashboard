# Space Weather Launch Decision Support Prototype

> August AI Builders Challenge — Space Exploration theme
> IBM Bob was the primary AI development environment used to build this prototype.
> Licensed MIT. See [`LICENSE`](LICENSE).

## Status and claim ceiling

Read this before anything else in this document.

**The model is a challenge prototype. It is not operationally qualified and must not inform a real launch decision.** The bundled classifiers were trained on synthetic launch fixtures, and their performance figures demonstrate that the software path works end to end — not that the predictions are valid. No part of this repository has been certified for flight safety.

**The input data, by contrast, is live.** Solar flare, coronal-mass-ejection, geomagnetic-storm, and solar-energetic-particle events are fetched at runtime from the public [NASA DONKI](https://kauai.ccmc.gsfc.nasa.gov/DONKI/) API. [NOAA SWPC](https://www.swpc.noaa.gov/) is the intended source for Kp and F10.7 features. The distinction matters: the data pipeline is real, the trained model is a demonstration.

What is genuinely differentiating here is not the accuracy number — it is the **evidence architecture**. Every claim this application displays is traceable: model artifacts carry SHA-256 hashes verified against their metadata, evidence limits are stated in the interface rather than buried, and explanations are explicitly labeled when they are illustrative rather than model-derived. See [Evidence Limits](#evidence-limits) and [`SECRET_SCAN.md`](SECRET_SCAN.md).

## Problem

Space weather can affect launch vehicles, electronics, communications, and crewed missions. Operators need a clear way to inspect current solar activity, test a launch scenario, and understand what evidence supports an AI-assisted recommendation.

## Solution

This project is a Streamlit proof of concept that:

- fetches current NASA DONKI event data;
- accepts operator-controlled space-weather and launch inputs;
- runs a bundled prototype classifier;
- displays a GO, HOLD, or SCRUB decision-support result;
- exposes model metadata, artifact hashes, metrics, and explicit evidence limits.

The application is decision support only. It is not a certified flight-safety system and must not be used as operational launch authority.

## Selected Theme

**Space Exploration**

The prototype focuses on launch-window decision support under solar-flare, coronal-mass-ejection, and geomagnetic-storm conditions.

## AI Approach and Architecture

```text
NASA DONKI events
        +
operator scenario inputs
        |
        v
feature vector
        |
        v
prototype classifier
        |
        v
probability + GO/HOLD/SCRUB result
        |
        v
model metadata + hashes + claim ceiling
```

Three model implementations are included:

- Logistic Regression
- Random Forest
- XGBoost

The current bundled artifacts were generated from synthetic test data. Their metrics demonstrate the software path, not real-world predictive validity or operational qualification.

## Working Prototype Evidence

Verified locally on August 30, 2026 by direct execution:

| Check | Result |
|---|---|
| Streamlit application | HTTP 200 at `http://127.0.0.1:8501/` |
| Live data path | NASA DONKI response rendered in the browser |
| Model inference | Bundled XGBoost artifact loaded and returned a probability |
| Model Lab | Three model artifacts and metadata rendered without traceback |
| Prediction Explorer | Interactive inference page rendered with the bundled model |
| Automated tests | `59 passed` |
| Artifact integrity | All three model SHA-256 values matched their metadata |
| Notebooks | All five parse as valid notebook JSON |

The `59 passed` figure was independently re-confirmed on 2026-08-30 via `python -m pytest tests/ -q`: 59 tests collected across five test modules, all passing. (On Windows the run exits non-zero on a pytest temporary-directory cleanup `PermissionError` *after* all tests report green; this is a local filesystem artifact, not a test failure, and does not occur on the Linux runner used by CI.)

**This table records that each surface loaded and returned a result. It does not certify that every rendered value is correct.** Known defects were under active repair at the time of writing, and a page can load successfully while still displaying a wrong number. Treat the table as evidence of a working software path, not of output correctness — the [Evidence Limits](#evidence-limits) section below is the binding statement.

## Evidence Limits

- The model artifacts and displayed metrics are synthetic-demo evidence only.
- The notebooks are structurally valid but are not stored with executed outputs.
- `FEATURE_PROVENANCE.json` has not yet been generated for a complete training dataset.
- SHAP values are explicitly labeled illustrative or synthetic when no compatible model-backed explanation is available.
- A successful local run does not establish deployment, production readiness, launch safety, or regulatory approval.

### On the deliberate absence of performance numbers

**This README quotes no accuracy, precision, recall, or ROC-AUC figure, and that omission is intentional.** Publishing a headline metric here would be the single easiest way to make this document dishonest, for three independent reasons:

1. The bundled models were trained on **synthetic** launch fixtures. Any resulting score measures self-consistency on generated data, not predictive skill against real space weather.
2. The validation split is approximately **15 rows**. At that size a single reclassified sample moves the reported accuracy by several percentage points, so the metric carries no meaningful precision. Any figure quoted anywhere in this project must state its sample size beside it.
3. Two computational defects were identified in the metrics pipeline and were under repair when this section was written: an **inverted probability column** feeding the score, and **ROC-AUC computed from hard labels rather than predicted probabilities** — a well-known error that yields a number that looks plausible but is not the AUC.

Metrics will be published only once those defects are corrected, the models are retrained, and the figure can be stated together with its sample size. Until then the machine-readable values in `dashboard/models/metrics_summary.json` and the `*_metadata.json` files should be read as **software-path artifacts, not performance claims**.

The verifiable claims in this project are the ones a reader can check: the data source is live and public, the model artifact hashes match their metadata, and the evidence limits are declared rather than implied.

## Quick Start

```powershell
cd space-weather-dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run dashboard/app.py
```

Open `http://127.0.0.1:8501/`.

The NASA API key is optional for light demo use. To use your own key:

```powershell
$env:NASA_API_KEY = '<your NASA API key>'
python -m streamlit run dashboard/app.py
```

Never commit the key.

## Tests

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m pytest -q -p no:cacheprovider
```

The model tests write only to pytest temporary directories. They do not overwrite the bundled dashboard artifacts.

## Data Sources

| Source | Use |
|---|---|
| [NASA DONKI](https://kauai.ccmc.gsfc.nasa.gov/DONKI/) | Solar flares, CMEs, geomagnetic storms, and solar energetic particles |
| [NOAA SWPC](https://www.swpc.noaa.gov/) | Intended source for Kp and F10.7 historical features |
| Synthetic launch fixtures | Prototype training and automated test behavior |

## Notebooks

| Notebook | Purpose | Current evidence state |
|---|---|---|
| `01_data_ingestion.ipynb` | NASA DONKI ingestion | Valid JSON, unexecuted |
| `02_eda_and_cleaning.ipynb` | Cleaning and exploratory analysis | Valid JSON, unexecuted |
| `03_feature_engineering.ipynb` | Feature construction and provenance | Valid JSON, unexecuted |
| `04_model_training.ipynb` | Model training and evaluation | Valid JSON, unexecuted |
| `05_evaluation_and_explainability.ipynb` | SHAP and evaluation views | Valid JSON, unexecuted |

## How IBM Bob Was Used

**IBM Bob was the primary AI development environment used to design and implement this application. Aevion's verification and release tooling independently qualified the final build.**

Bob was the tool in which the prototype was designed and written. It was used to:

- scaffold the repository structure and module layout;
- implement the NASA DONKI ingestion layer and the feature-engineering modules;
- build the multi-page Streamlit interface, including the custom space theme and CSS design-token system;
- implement the three model-training paths (Logistic Regression, Random Forest, XGBoost);
- author the pytest suite and the GitHub Actions CI workflow;
- draft the project documentation and the analysis notebooks.

Bob is not claimed as the executor of every step, and the requirement is that it was the *primary* development tool rather than the exclusive one. Independent of Bob, Aevion's own verification and release tooling performed the final qualification pass: the pre-publication credential scan documented in [`SECRET_SCAN.md`](SECRET_SCAN.md), local execution and browser validation of the running application, model-artifact hash verification against stored metadata, review of every factual claim in this README against an openable artifact in the repository, and the release-readiness tracking in [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md).

That split is deliberate and is the honest description of how the work happened: Bob built it, and a separate toolchain checked it before it was released.

## License

MIT — see [`LICENSE`](LICENSE). The license carries an additional notice stating that this software is not qualified for operational launch, flight-safety, or space-weather decisions.

## Release Documentation

| Document | Purpose |
|---|---|
| [`SECRET_SCAN.md`](SECRET_SCAN.md) | Pre-publication credential scan — scope, patterns, findings, re-scan procedure |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Path to a public URL, prerequisites, and NASA key handling via platform secrets |
| [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) | Challenge requirement tracking with evidence and current status |
| [`docs/architecture.md`](docs/architecture.md) | System architecture detail |

## Repository Layout

```text
space-weather-dashboard/
|-- dashboard/app.py
|-- dashboard/components/
|-- dashboard/pages/
|-- dashboard/models/
|-- notebooks/
|-- tests/
|-- docs/architecture.md
|-- requirements.txt
`-- .github/workflows/ci.yml
```
