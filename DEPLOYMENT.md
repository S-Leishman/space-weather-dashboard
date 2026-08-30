# Deployment — Path to a Public URL

**Status: SCOPED, NOT EXECUTED. Nothing in this document has been deployed.**
**Lane:** RELEASE-INFRA-001 · **Date:** 2026-08-30

Deployment is deliberately gated. It must not happen until the in-flight application defect fixes have landed and an independent verifier has confirmed the application runs correctly. Publishing a build that renders raw JavaScript to a public URL is a worse outcome than publishing nothing, because the URL is what a judge opens first.

## Recommended path: Streamlit Community Cloud

| | |
|---|---|
| **Cost** | Free |
| **Time to live URL** | ~10 minutes, mostly unattended dependency build |
| **Prerequisite** | A **public** GitHub repository |
| **Secrets** | Built-in encrypted secrets manager — no credential in the repository |
| **URL shape** | `https://<app-name>.streamlit.app` |

This is the shortest credible path. It is Streamlit's own first-party hosting, it reads `requirements.txt` and `runtime.txt` directly, it needs no Dockerfile or server configuration, and it handles TLS and the public hostname automatically.

**Why not Cloudflare:** no Cloudflare Pages or Workers configuration exists in this repository, and Cloudflare's platforms do not run a long-lived Python WebSocket server like Streamlit without additional container infrastructure (Workers is a JavaScript/WASM edge runtime; Pages serves static assets). Routing this app through Cloudflare would mean standing up a container host and putting Cloudflare in front of it — strictly more work and more failure surface than the first-party option, with no benefit under a 30-hour deadline. If a Cloudflare-fronted deployment is wanted later, it should be a post-submission task.

## Prerequisite status

| # | Prerequisite | Status | Detail |
|---|---|---|---|
| 1 | Entrypoint file | **PASS** | `dashboard/app.py` — set this as the "Main file path" in the Streamlit Cloud form |
| 2 | `requirements.txt` present and parseable | **PASS** | 20 declared dependencies, valid pip requirements syntax |
| 3 | Pinned Python version | **PASS** (added by this lane) | `runtime.txt` → `3.11`, matching the CI matrix |
| 4 | Streamlit platform config | **PASS** | `.streamlit/config.toml` — `headless = true`, XSRF protection on, usage stats off. Correct for hosted deployment |
| 5 | Secrets handled without committed files | **PASS** | NASA key is read from the masked UI input or the `NASA_API_KEY` environment variable. `.streamlit/secrets.toml` is gitignored and does not exist |
| 6 | No credentials in repository | **PASS** | See [`SECRET_SCAN.md`](SECRET_SCAN.md) — clean scan, no git history to contaminate |
| 7 | Public GitHub repository | **NOT STARTED — owner-gated** | No repository exists yet, public or private. This is the hard prerequisite and requires owner authorization |
| 8 | Dependency versions pinned | **MISSING — see below** | Every dependency is `>=`, so no two builds are guaranteed identical |
| 9 | Runtime dependency set minimized | **MISSING — see below** | `requirements.txt` includes notebook and test tooling not needed to serve the app |
| 10 | Application defects resolved | **BLOCKED — external** | Owned by the concurrent application-fix lane. **This is the gate on deploying at all** |
| 11 | Independent run verification | **BLOCKED — external** | A separate verifier must confirm the app runs before a public URL exists |

## The two dependency gaps, and why they matter

Both are real deployment risks rather than style preferences, and both live in `requirements.txt`.

**Note on ownership:** `requirements.txt` is shared with the concurrent application-fix lane, which may be adding dependencies. To avoid a collision it has **not** been edited by this lane. The changes below are specified for whoever commits last, and should be applied in a single pass immediately before deployment.

### Gap 8 — Unpinned versions make the build non-reproducible

Every entry uses `>=`:

```
numpy>=1.26.0
scikit-learn>=1.3.0
shap>=0.43.0
xgboost>=2.0.0
```

On Streamlit Cloud, pip resolves these fresh at build time, so the hosted app may not run the versions that were tested locally. The concrete hazard is `numpy>=1.26.0`, which resolves to NumPy 2.x, against which older `shap` and `scikit-learn` builds have known binary-incompatibility failures. **This is the most likely cause of a deployment that builds locally and fails in the cloud**, and it surfaces as an import-time crash on the hosted instance rather than a warning.

**Fix:** capture the working local versions and pin them exactly.

```powershell
# From an activated venv where the app is confirmed working:
python -m pip freeze > requirements.lock.txt
```

Then set exact `==` pins in `requirements.txt` for at least `numpy`, `pandas`, `scikit-learn`, `xgboost`, `shap`, and `streamlit`.

### Gap 9 — Notebook and test tooling ships to production

`requirements.txt` includes packages the served application never imports:

```
notebook>=7.0.0        ipykernel>=6.25.0      ipywidgets>=8.1.0
pytest>=7.4.0          pytest-cov>=4.1.0
seaborn>=0.13.0        matplotlib>=3.8.0      tqdm>=4.66.0
```

These lengthen the cold build, consume container memory against the free tier's ~1 GB limit, and enlarge the dependency surface. `notebook` and `ipykernel` in particular pull in a large transitive tree.

**Fix:** move development-only dependencies to a separate `requirements-dev.txt` and have CI install both. Verify before removing — `matplotlib` and `seaborn` may be imported by the SHAP rendering path, and `plotly`, `shap`, `joblib`, `pyarrow`, `requests`, and `python-dateutil` are all genuinely required at runtime.

## NASA API key — correct handling

The application already handles the key correctly and **no change is required**. It works unauthenticated against NASA's rate-limited `DEMO_KEY`, so the app functions on a public URL with no secret configured at all. The key only raises the rate limit.

Three supported channels, none of which involve a committed file:

1. **Masked UI input** — `dashboard/app.py:105`, `st.text_input(..., type="password")`. Per-session, never persisted.
2. **Environment variable** — `NASA_API_KEY`, read via `os.environ.get`.
3. **Platform secrets** — Streamlit Cloud's encrypted store, entered through the dashboard UI at *App settings → Secrets*:

```toml
NASA_API_KEY = "your-key-here"
```

Streamlit injects this at runtime as `st.secrets`. **It is never written to the repository.** Do not create `.streamlit/secrets.toml` locally and commit it — that file is gitignored precisely to prevent this, and it is the most common way a key reaches a public repository.

A free key is available at <https://api.nasa.gov/>.

## Deployment procedure — for execution only after gates 7, 10, and 11 clear

Do not begin until the application fixes have landed and an independent verifier has confirmed a correct local run.

1. **Re-run the secret scan.** Application code changed after the original scan. Follow the re-scan block in [`SECRET_SCAN.md`](SECRET_SCAN.md). Do not proceed on a dirty result.
2. **Pin dependencies** (Gap 8) and, optionally, split dev dependencies (Gap 9). Confirm the app still runs locally afterward.
3. **Owner authorizes public visibility**, then the repository is made public. Irreversible in practice — a public repository can be cloned and cached within seconds, so reverting visibility does not recall the copies.
4. **Confirm CI is green** on the public repository before deploying. See the CI section in [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) — note the workflow triggers on `main` only, so the default branch must be named `main` for it to run at all.
5. **Create the app** at <https://share.streamlit.io> → *New app*:
   - Repository: the public repository
   - Branch: `main`
   - Main file path: `dashboard/app.py`
   - Python version: `3.11`
6. **Add the NASA key** under *App settings → Secrets*, if a real key is being used. Optional — `DEMO_KEY` works without it.
7. **Wait for the build.** First build takes several minutes; `xgboost`, `shap`, and `pyarrow` are the slow wheels.
8. **Verify the live URL in a browser** — not just an HTTP 200. Load every page, confirm no raw JavaScript or HTML is rendered as visible text, confirm the charts draw, and confirm the live NASA data path returns events.
9. **Record the URL** in `SUBMISSION_CHECKLIST.md` and in the challenge project page.

## Rollback

Streamlit Cloud deployments are reversible, which is worth stating because the repository visibility change in step 3 is not. An app can be deleted from the Streamlit dashboard, immediately removing the public URL. Redeploying is a rerun of steps 5–8.

The irreversible step in this procedure is making the repository public. Everything after it can be undone.
