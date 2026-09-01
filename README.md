# Aevion SpaceOps

**Evidence-gated space-weather mission decision support.**

Aevion SpaceOps is a student prototype for the **August AI Builders Challenge with IBM Bob**. It combines live space-weather data, prototype model scoring, evidence and provenance records, explicit policy state, and a human decision boundary.

> **Status:** IMPLEMENTED prototype. **Not operationally qualified for launch, flight, or safety-critical decision making.** The bundled training label is synthetic and independent of the features, so the current model artifacts do **not** demonstrate predictive skill. Model outputs are presented as prototype scores, not launch probabilities.

## Problem Statement

Space-weather events such as solar flares, coronal mass ejections, and geomagnetic storms can affect launch operations, spacecraft electronics, communications, and other mission systems. A prediction alone is not enough for a consequential decision: an operator also needs to know which model ran, what data and artifacts were used, whether the evidence is complete, and who retains authority to act.

## Solution

Aevion SpaceOps demonstrates an evidence-gated mission-decision workflow:

1. retrieve space-weather inputs,
2. derive model features,
3. generate a prototype model score,
4. assemble evidence and provenance,
5. expose policy state as `PASS`, `FAIL`, `HOLD`, or `UNKNOWN`, and
6. leave the consequential mission decision to a human.

The model is an input to the workflow, not the authority boundary. The prototype never launches, aborts, or authorizes a mission.

## Working Demo

The Streamlit application contains five reviewable surfaces:

- Mission Control / Home
- Data Pipeline
- Model Lab
- Prediction Explorer
- About

Run it locally with:

```bash
python -m pip install -r requirements.txt
streamlit run dashboard/app.py
```

The Home page performs the browser-demonstrated live NASA DONKI fetch. A public hosted URL is recorded separately in the challenge submission once deployment is complete.

## AI Approach and Architecture

The current prototype is organized as five separable layers:

```text
NASA space-weather ingestion
        ↓
feature engineering
        ↓
bundled model inference
        ↓
evidence + provenance + policy state
        ↓
human mission decision
```

The repository implements:

- NASA DONKI retrieval and retry handling;
- feature engineering including Kp, F10.7-derived, lag, event, CME, and time features;
- Logistic Regression, Random Forest, and XGBoost training/inference paths;
- bundled model artifacts and companion metadata;
- Streamlit presentation, scenario controls, provenance views, and receipt generation.

The checked-in model artifacts were generated from the synthetic fixture used by the model tests. Their role is to demonstrate the software and evidence path, not to establish operational forecasting accuracy.

## Evidence and Provenance

The prototype exposes evidence rather than presenting a model score as self-authenticating. The reviewed flow records or displays items such as:

- model identity;
- model artifact SHA-256;
- input values;
- feature-artifact identity and provenance;
- policy state and reasons;
- timestamps;
- receipt/hash material used to detect drift.

The Data Pipeline page also surfaces missing evidence rather than silently suppressing it. In the reviewed build, missing raw-ingest artifacts are called out explicitly.

## Human Authority and Safety Boundary

The decision boundary is intentionally outside the model:

```text
MODEL OUTPUT != AUTHORITY
```

A `HOLD` or `UNKNOWN` state is not treated as permission to act. The software provides a reviewable record for a person who retains mission authority.

## Selected Challenge Theme

**August Challenge: Advance Space Exploration with AI.**

The project focuses on applying AI to space-weather mission decision support while making evidence, limitations, and human authority visible to the operator.

## How IBM Bob Was Used

**IBM Bob was the primary development tool.** The application was built in Bob across seven development phases covering:

1. project scaffolding,
2. NASA and NOAA ingestion work,
3. feature engineering,
4. model training,
5. dashboard construction,
6. tests and CI, and
7. the multi-page frontend.

After the Bob development session, separate tooling was used for an independent correctness and release review. That review repaired defects, tightened claim language, verified evidence paths, and checked the final submission candidate. Those later checks are qualification work, not a claim that another tool replaced Bob as the primary development environment.

## Data Sources

The prototype uses or references:

- **NASA DONKI** for the demonstrated live event-ingestion path;
- **NOAA / SWPC-derived solar and geomagnetic context** used by the broader feature-engineering work.

The current artifact does not claim a complete historical operational training corpus.

## Verification / Tests

The repository includes automated tests covering ingestion, feature engineering, model behavior, evidence positioning, frontend behavior, cross-page coherence, and regression cases.

Run:

```bash
python -m pytest -q
```

The submission is frozen only after an external GitHub Actions run succeeds on the exact reviewed commit. Test success establishes software behavior covered by those tests; it does not establish mission suitability or forecasting accuracy.

## Known Limitations

- The current training label is **synthetic** and independent of the model features.
- Therefore the checked-in models have **no demonstrated predictive skill** for real launch decisions; near-random validation performance is expected from that synthetic setup.
- Prototype model scores are **not launch probabilities**.
- The current dashboard live path is NASA DONKI; the repository does not claim a complete live NOAA ingestion path in the reviewed build.
- F10.7 short-window features are derived from available source material and are not claimed to reproduce authentic short-window solar variability.
- The Prediction Explorer simplifies some inputs for demonstration.
- Model-backed SHAP explanation is **not currently available as an operationally verified feature**; the reviewed interface labels unavailable/illustrative explanation behavior accordingly.
- This software is **not operationally qualified** for launch, aviation, spacecraft, emergency, or other safety-critical use.

## Author

**Scott Leishman** — student entrant and founder of Aevion LLC.

## License

See [`LICENSE`](LICENSE).