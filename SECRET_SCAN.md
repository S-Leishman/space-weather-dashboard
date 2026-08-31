# Secret Scan — Pre-Public-Release Gate

**Target:** `space-weather-dashboard/`
**Scan date:** 2026-08-30
**Lane:** RELEASE-INFRA-001
**Result: CLEAN — no credentials found. One non-credential hygiene item (personal filesystem paths) is listed below and must be cleared before the repository is made public.**

This document exists so that the decision to make this repository public is defensible: it records exactly what was scanned, with which patterns, and what was found.

## Scope of exposure at scan time

A key finding that bounds the entire risk surface:

| Question | Answer | How verified |
|---|---|---|
| Is `space-weather-dashboard/` its own git repository? | **No.** No `.git` directory exists inside it. | `Test-Path .git` → `False` |
| Is it tracked by the parent estate repository? | **No.** Zero files tracked, zero commits. | `git ls-files space-weather-dashboard` → 0 lines; `git log -- space-weather-dashboard` → 0 lines |
| Does any git history for this application exist anywhere? | **No.** | `git log --all --oneline -- "space-weather-dashboard/**"` → 0 lines |
| Did a GitHub repository for it exist at scan time? | **No.** | `gh repo list S-Leishman --limit 100` → no entry; `gh api repos/S-Leishman/space-weather-dashboard` → **HTTP 404** |

**Consequence:** there was **no git history to scan** at scan time, because none had ever been created, and there was **no existing public exposure**. The classic failure mode — a credential removed from the working tree but still reachable in an old commit — is structurally impossible here.

### State after this lane

The scan above was performed on the bare working tree. History was then created *from that scanned tree*:

| | |
|---|---|
| Local repository | Initialized on branch `main` |
| Initial commit | `f5ac06c` — 46 files, the entire history of this repository |
| Excluded by `.gitignore` | `__pycache__/`, `.pytest_cache/`, `streamlit_stdout.log` — verified absent from the commit |
| Remote | `https://github.com/S-Leishman/space-weather-dashboard` — **PRIVATE** and **EMPTY** (push pending an OAuth scope grant) |

`streamlit_stdout.log`, a runtime log produced during local testing, was scanned separately before being excluded — 701 bytes, no credential, no personal path. It is gitignored so it cannot enter history later.

**The single commit is the complete history, and it was made from the tree scanned above.** That property is what makes the eventual public release defensible, and it must be preserved: any credential committed from here forward would remain reachable in history even after deletion from the working tree.

## What was scanned

The complete working tree of `space-weather-dashboard/` — 38 text and binary files — including hidden files and files that would otherwise be ignored (`--hidden --no-ignore`), covering:

- application source (`dashboard/**`)
- tests (`tests/**`)
- notebooks (`notebooks/*.ipynb`, including any embedded cell outputs)
- model artifacts and metadata (`dashboard/models/**`, `.joblib` binaries read as raw bytes)
- CI and platform configuration (`.github/workflows/ci.yml`, `.streamlit/config.toml`)
- dependency and project manifests (`requirements.txt`, `pyproject.toml`)
- documentation (`README.md`, `docs/**`)

## Patterns used

Credential-shaped literals, case-insensitive, via `ripgrep`:

```
api[_-]?key            secret                 token
password               passwd                 credential
BEGIN [A-Z ]*PRIVATE KEY
AKIA[0-9A-Z]{16}       (AWS access key ID)
ghp_[A-Za-z0-9]{20,}   (GitHub personal access token)
sk-[A-Za-z0-9]{20,}    (OpenAI-style key)
xox[baprs]-            (Slack token)
DEMO_KEY               (NASA placeholder — confirm it is the placeholder, not a real key)
<HOME>         (personal filesystem path / PII)
```

Credential-bearing **file types**, by name and extension:

```
.env  .env.*  *.pem  *.key  *.p12  *.pfx  *.crt  secrets.toml  credentials*
```

High-entropy literal sweep, to catch a secret that matches none of the above:

```
[A-Za-z0-9_\-]{32,}    (any 32+ character token-shaped string)
```

Binary sweep — each `.joblib` model artifact was read as raw bytes and ASCII-decoded, then searched for `api_key`, `secret`, `token`, `password`, `Scott`, `AKIA`, `ghp_`. A pickled model can carry strings that no text-oriented scanner sees; this closes that gap.

## Findings

### No credentials — confirmed

| Check | Result |
|---|---|
| `.env` or `.env.*` files | **None exist** |
| Private keys, certificates, keystores (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`) | **None exist** |
| `secrets.toml` / `credentials*` | **None exist** |
| AWS / GitHub / OpenAI / Slack key formats | **No matches** |
| Connection strings | **None** — the application makes only unauthenticated public HTTPS calls to NASA DONKI and NOAA SWPC |
| Hardcoded credential in any `.joblib` artifact | **No matches** |

Every hit on `api_key` / `token` / `password` was inspected individually and is benign:

- `dashboard/components/ingestion.py`, `dashboard/components/utils.py` — `api_key: str = "DEMO_KEY"` function parameters. `DEMO_KEY` is NASA's own published, rate-limited placeholder for unauthenticated access. It is not a credential and grants nothing beyond what an anonymous caller already has.
- `dashboard/app.py:105-111` — a Streamlit `st.text_input(..., type="password")` widget. This is the **correct** pattern: the key is supplied at runtime by the user, masked in the UI, and never written to disk.
- `tests/test_ingestion.py`, `tests/test_dashboard_utils.py` — literals `"TEST"` and `"FAIL"` passed to mocked HTTP calls. No network egress.
- `tests/test_frontend.py`, `dashboard/assets/css/space_theme.css` — "token" in the CSS **design token** sense (colors, spacing). Unrelated to authentication.
- `README.md:94` — `$env:NASA_API_KEY = '<your NASA API key>'`, a documentation placeholder, immediately followed by the instruction "Never commit the key."
- `notebooks/01_data_ingestion.ipynb` — `os.environ.get('NASA_API_KEY', 'DEMO_KEY')`, reading from the environment with a safe default. Correct pattern.

The high-entropy sweep returned only two classes of string, both legitimate:

- **64-character hex values** in `dashboard/models/*_metadata.json` — these are SHA-256 integrity hashes of the model artifacts. They are verification evidence and are *intended* to be published; a hash is not a secret.
- **Long `snake_case` test function names** in `tests/**`.

Notebook cell outputs were included in the sweep. No credential was found embedded in stored output.

### HOLD-1 — Personal filesystem paths in model metadata (not a credential)

Three files contain the absolute build path of the owner's machine:

```
dashboard/models/xgboost_metadata.json:17
dashboard/models/logistic_regression_metadata.json:20
dashboard/models/random_forest_metadata.json:22

  "model_file": "<REPO_ROOT>\\dashboard\\models\\<name>.joblib"
```

**Severity: low. This is not a blocker for the secret scan, and it grants no access.** It is an information-hygiene item: it publishes the owner's Windows username and local directory layout. Standard practice is to store a path relative to the repository root instead.

**This is not mine to fix.** `dashboard/models/**` metadata is generated by the model-training code, which is owned by the concurrent RELEASE-POLISH-001 lane. Editing it here would either collide with that lane's work or be overwritten the next time models are regenerated. It is handed off in the report rather than patched.

**Recommended fix (for the code owner):** emit `model_file` as a repository-relative path (e.g. `dashboard/models/xgboost.joblib`) when writing metadata. This also makes the metadata portable, which the current absolute path is not — a reader who clones the repository cannot resolve it.

## Controls added by this lane

A `.gitignore` was authored for this repository before any commit exists, so the following can never enter history:

- `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `.streamlit/secrets.toml` — credential-bearing paths, blocked pre-emptively
- `__pycache__/`, `.pytest_cache/`, `.venv/`, `*.pyc` — build and cache noise present in the working tree at scan time

## Limits of this scan

Stated plainly, so the result is not over-read:

- The scan covers the working tree **as of 2026-08-30**. The RELEASE-POLISH-001 lane is concurrently editing application code. **Any file changed after this scan is outside its coverage.**
- Pattern-based scanning cannot prove the absence of a secret that matches no known credential format and has entropy below the 32-character threshold. The binary and high-entropy sweeps narrow this gap but do not eliminate it.
- A clean scan is a necessary condition for public release, not a sufficient one. Owner authorization is separately required.

## Re-scan requirement before publication

**This scan must be re-run immediately before the repository is made public**, because application code is changing underneath it. The re-scan is cheap; the mistake it prevents is not. Making a repository public is irreversible in practice — it can be cloned and cached by third parties within seconds, so revoking visibility does not revoke the copies.

Re-run from `space-weather-dashboard/`:

```powershell
rg --hidden --no-ignore -n -i `
  -e "api[_-]?key" -e "secret" -e "token" -e "password" -e "credential" `
  -e "BEGIN [A-Z ]*PRIVATE KEY" -e "AKIA[0-9A-Z]{16}" -e "ghp_[A-Za-z0-9]{20,}" `
  -e "sk-[A-Za-z0-9]{20,}" -e "xox[baprs]-" -e "<HOME>" `
  -g '!**/__pycache__/**' -g '!**/.git/**' -g '!*.joblib'

Get-ChildItem -Recurse -Force -File -Include ".env",".env.*","*.pem","*.key","*.p12","*.pfx","secrets.toml","credentials*"
```

The scan is clean when the first command returns only the benign classes enumerated above and the second returns nothing.

## Standing estate rule

Credentials are never committed to any file. The NASA API key is supplied at runtime — through the masked UI input, the `NASA_API_KEY` environment variable, or the hosting platform's secrets manager — and never through a file in this repository. See `DEPLOYMENT.md` for the platform secrets configuration.
