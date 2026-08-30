# Architecture

## Current Prototype

The application has five separable layers:

1. NASA event ingestion
2. data cleaning and exploration notebooks
3. feature engineering
4. model training and inference
5. Streamlit presentation

The current checked-in prototype proves the live NASA fetch, scenario controls, bundled-model inference, model metadata display, and browser rendering. It does not contain a completed historical training dataset or executed notebook outputs.

## Data Ingestion

`dashboard/components/ingestion.py` implements NASA DONKI retrieval, retry handling, response storage, and a manifest path. `dashboard/app.py` performs the browser-demonstrated live fetch.

The notebooks describe a broader historical pipeline. Those notebooks are valid JSON but remain unexecuted in the current artifact.

## Feature Engineering

`dashboard/components/features.py` implements rolling Kp and F10.7 features, lag features, event flags, CME scoring, and cyclical time encoding. Its save path is `dashboard/data/processed/`.

`FEATURE_PROVENANCE.json` is produced only when the feature-save path is executed. That file is not present in the current prototype, so full training-data provenance is not claimed.

## Model Training and Inference

`dashboard/components/model_trainer.py` implements Logistic Regression, Random Forest, and XGBoost training. Models and companion metadata are written to `dashboard/models/`.

The bundled model artifacts were generated from the synthetic fixture used by `tests/test_model.py`. Their SHA-256 values match their metadata. The metrics demonstrate the software path only and are not operational qualification evidence.

The dashboard loads the bundled XGBoost artifact for inference. If a model-backed SHAP explanation is unavailable, the interface labels the displayed explanation as illustrative or synthetic.

## Streamlit Interface

`dashboard/app.py` provides Mission Control. The page modules provide:

- Data Pipeline
- Model Lab
- Prediction Explorer
- About

Browser verification on August 30, 2026 rendered Mission Control, Model Lab, and Prediction Explorer without traceback after the final fixes.

## Automated Validation

The local command below passes 59 tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m pytest -q -p no:cacheprovider
```

The model tests redirect generated artifacts to pytest temporary directories, preventing test execution from overwriting the bundled dashboard artifacts.

`.github/workflows/ci.yml` defines the corresponding GitHub Actions workflow. A remote CI run is not claimed until the project is published and the workflow completes.
