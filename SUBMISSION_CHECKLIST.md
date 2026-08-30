# Submission Checklist — August AI Builders Challenge

**Deadline: 2026-08-31, 11:59 PM ET**
**Compiled:** 2026-08-30 · **Lane:** RELEASE-INFRA-001

Every row states a real status backed by an artifact a reader can open. Nothing is marked complete on the assumption that it will be.

**Legend** — `PASS` verified with evidence · `HOLD` blocked or awaiting something named · `HOLD_EVIDENCE` may already be done, but no proof has been supplied · `NOT_STARTED` no work exists yet

## Requirement status

| # | Requirement | Status | Evidence / blocker |
|---|---|---|---|
| 1 | Working prototype | **HOLD** | Runs and all 59 tests pass, but known rendering and metrics defects are under repair. See row 1 detail |
| 2 | IBM SkillsBuild activity completion | **HOLD_EVIDENCE** | **Owner-only.** No completion evidence located. A prior Gmail search found no completion email. Not asserted as done |
| 3 | Public GitHub repository | **HOLD** | A **PRIVATE** repository now exists at `S-Leishman/space-weather-dashboard`, but it is **empty** — the first push was rejected for a missing OAuth scope. See row 3 detail. Making it public is owner-gated |
| 4 | README with all required sections | **PASS** | [`README.md`](README.md) — all five sections present. See section map below |
| 5 | Published challenge project page | **NOT_STARTED** | **Owner-only.** Requires the public repository URL (row 3) and the video URL (row 6) |
| 6 | Public video, ≤ 3 minutes | **NOT_STARTED** | **Owner-only.** Not recorded. Out of scope for this lane by instruction |
| 7 | Owner clicks Publish before deadline | **NOT_STARTED** | **Owner-only.** Terminal, irreversible action |
| 8 | License | **PASS** | [`LICENSE`](LICENSE) — MIT, plus a not-for-operational-use notice |
| 9 | Pre-publication secret scan | **PASS** | [`SECRET_SCAN.md`](SECRET_SCAN.md) — clean. **Must be re-run before going public** |
| 10 | `.gitignore` protecting credentials | **PASS** | [`.gitignore`](.gitignore) — blocks `.env`, keys, `.streamlit/secrets.toml` before any commit exists |
| 11 | CI pipeline | **HOLD** | Workflow file is valid but **has never executed**. Two defects found — see CI section |
| 12 | Public deployment URL | **HOLD** | Scoped in [`DEPLOYMENT.md`](DEPLOYMENT.md), deliberately not executed. Gated on rows 1 and 3 |

### Row 1 detail — working prototype

The software path is verified: the Streamlit app serves HTTP 200 locally, the live NASA DONKI fetch returns data, all three model artifacts load and return probabilities, and 59 of 59 tests pass (`python -m pytest tests/ -q`, re-confirmed 2026-08-30).

It is **not** marked PASS because a page can load while displaying a wrong value. Defects under active repair at the time of writing include a raw-JavaScript rendering leak, an inverted probability column, ROC-AUC computed from hard labels instead of probabilities, a blank feature-importance chart, and the SHAP panel. This row flips to PASS only when those fixes land and an independent verifier confirms a correct run — not merely a run.

### Row 3 detail — repository state and the push blocker

Local git repository initialized and committed. Remote created **private** and wired as `origin`, but **nothing has been pushed yet**.

```
$ gh repo view S-Leishman/space-weather-dashboard --json visibility,isEmpty
{"visibility":"PRIVATE","isEmpty":true}
```

| | |
|---|---|
| Local branch | `main` (chosen so `.github/workflows/ci.yml` will actually trigger — see CI-1) |
| Local HEAD | `f5ac06c` — `chore(release): initialize repository with release infrastructure` |
| Files committed | 46 · working tree clean · no caches, logs, or credentials |
| Remote | `https://github.com/S-Leishman/space-weather-dashboard` — **PRIVATE, EMPTY** |

**Blocker — missing `workflow` OAuth scope.** The push was rejected by GitHub:

```
! [remote rejected] HEAD -> main
  (refusing to allow an OAuth App to create or update workflow
   .github/workflows/ci.yml without `workflow` scope)
```

The authenticated `gh` token holds `gist`, `read:org`, and `repo`, but not `workflow`, so it may not create a file under `.github/workflows/`. This is a GitHub-side protection, not a repository misconfiguration, and nothing is wrong with the commit.

**Resolution is owner-only** because granting the scope requires an interactive browser authorization:

```powershell
gh auth refresh -h github.com -s workflow
cd "C:\Users\Scott\Desktop\Aevion LLC\space-weather-dashboard"
git push -u origin main
```

The repository stays private through this step. Roughly 2 minutes.

### Row 2 detail — IBM SkillsBuild

**This is deliberately not marked complete, and should not be marked complete without a screenshot or completion email.** It is a hard eligibility requirement that no amount of code quality substitutes for. If it has not been done, it is the cheapest remaining item to finish and the most expensive one to discover missing after the deadline. Owner should verify directly in the SkillsBuild portal.

## README required-section map

Requirement 4 is satisfied. Each required section maps to a heading in [`README.md`](README.md):

| Required section | Heading | Content |
|---|---|---|
| The problem | `## Problem` | Space-weather impact on launch vehicles, electronics, comms, crewed missions |
| The solution | `## Solution` | Streamlit decision-support prototype; live DONKI fetch, scenario inputs, GO/HOLD/SCRUB output with evidence surfaced |
| AI approach and architecture | `## AI Approach and Architecture` | Pipeline diagram, three model implementations, claim ceiling. Extended in [`docs/architecture.md`](docs/architecture.md) |
| Selected theme | `## Selected Theme` | Space Exploration |
| How IBM Bob was used | `## How IBM Bob Was Used` | Bob as the primary AI development environment; Aevion tooling independently qualified the final build |

Supporting sections added or strengthened by this lane: `Status and claim ceiling`, `On the deliberate absence of performance numbers`, `License`, `Release Documentation`, and an honesty caveat on the prototype-evidence table.

**Claim hygiene:** the README quotes **no** accuracy, precision, recall, or ROC-AUC figure. This is intentional and documented in-line — the models were trained on synthetic fixtures, the validation split is roughly 15 rows, and two metric-computation defects were open. Any metric added later must state its sample size beside it.

## CI honesty — requirement 11

**A green CI badge must not be added to the README. There is nothing to be green about: the workflow has never run.**

Evidence, read-only, no workflows triggered or re-run:

```
$ gh api repos/S-Leishman/space-weather-dashboard
gh: Not Found (HTTP 404)

$ gh run list --repo S-Leishman/space-weather-dashboard --limit 5
failed to get runs: HTTP 404: Not Found
```

The repository does not exist, so GitHub Actions has executed zero times. `.github/workflows/ci.yml` is syntactically valid and its logic is sound, but it is **untested in CI**.

### CI-1 — Branch trigger mismatch (will silently never run)

`.github/workflows/ci.yml` triggers on `main` only:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

The parent estate repository's branch is `master`. If the new application repository is initialized with a `master` default branch, **CI will never fire and will report no status at all** — which reads as "no tests" to a reviewer, worse than a visible failure.

**Fix:** name the default branch `main` when initializing (`git init -b main`), or add `master` to both branch lists. Naming it `main` is preferable — it matches the workflow and GitHub's default.

### CI-2 — Unpinned dependencies make CI non-deterministic

The workflow runs `pip install -r requirements.txt`, where every dependency is `>=`. Two runs a week apart can install different versions, so CI can go red without any code change. The specific hazard is `numpy>=1.26.0` resolving to NumPy 2.x against older `shap`/`scikit-learn` wheels. Detail and fix in [`DEPLOYMENT.md`](DEPLOYMENT.md), Gap 8.

### What CI would likely do today

Best available assessment, stated as an expectation rather than a result: the test job would **probably pass**. All 59 tests pass locally, and the one local failure is a Windows-only pytest temporary-directory cleanup `PermissionError` that occurs *after* every test reports green and does not arise on `ubuntu-latest`.

This is a prediction from a local Linux-independent run, **not** an observed CI result. It becomes a fact only when a run appears in `gh run list`.

## Owner-only actions, in order

Only Scott can perform these. Everything up to the irreversible line has been prepared. Estimated hands-on cost: **roughly 20–30 minutes of clicks**, excluding the video recording and the dependency-build wait.

| Step | Action | Why only the owner | Est. |
|---|---|---|---|
| 1 | **Verify IBM SkillsBuild completion** in the SkillsBuild portal; capture a screenshot | Personal account credentials. Hard eligibility gate | 5 min |
| 2 | **Grant the `workflow` OAuth scope and push** — `gh auth refresh -h github.com -s workflow` then `git push -u origin main`. Repository stays private | Interactive browser authorization. See row 3 detail | 2 min |
| 3 | **Confirm the application fixes have landed** and an independent verifier reports a correct run | Do not publish a build that renders raw JavaScript | — |
| 4 | **Authorize the re-run secret scan** result (procedure in [`SECRET_SCAN.md`](SECRET_SCAN.md)) | Code changed after the original scan | 2 min |
| 4a | **Flip the repository to public** — `gh repo edit S-Leishman/space-weather-dashboard --visibility public --accept-visibility-change-consequences` | **IRREVERSIBLE.** A public repository can be cloned and cached within seconds; reverting visibility does not recall the copies | 1 min |
| 5 | **Confirm CI is green** on the public repository | Verify before claiming | 3 min |
| 6 | **Deploy to Streamlit Community Cloud** — steps 5–8 of [`DEPLOYMENT.md`](DEPLOYMENT.md) | Requires his GitHub-linked Streamlit account | 10 min + build |
| 7 | **Verify the live URL in a browser** — every page, no raw JavaScript, charts draw, live data returns | This is the last chance to catch a broken public deployment | 5 min |
| 8 | **Record and upload the video**, ≤ 3 minutes, publicly accessible | Requires his voice, screen, and account | 20–30 min |
| 9 | **Publish the challenge project page** with the repository URL and video URL | Requires his challenge-platform account | 10 min |
| 10 | **Click Publish** before 2026-08-31 11:59 PM ET | **TERMINAL AND IRREVERSIBLE** | 1 min |

Steps 1 and 8 are the two that cannot be shortened and do not depend on anything else — they can be done in parallel with the fix work, and doing so is the best use of the remaining time.

## Hard stop — what this lane did not do, by instruction

- Did **not** change any repository from private to public
- Did **not** deploy to any public URL
- Did **not** publish or submit anything on the challenge platform
- Did **not** record or upload video
- Did **not** force-push or rewrite git history
- Did **not** edit application code (`dashboard/**`, `tests/**`) — owned by the concurrent fix lane

## Hand-offs to the application-fix lane

Items found by this lane that fall inside application-code territory and were **not** touched:

1. **Personal filesystem paths in model metadata.** `dashboard/models/{xgboost,logistic_regression,random_forest}_metadata.json` each carry `"model_file": "C:\\Users\\Scott\\Desktop\\Aevion LLC\\..."`. Not a credential and not a release blocker, but it publishes the owner's username and local directory layout, and the absolute path is unresolvable for anyone who clones the repository. Fix: emit a repository-relative path when writing metadata. Detail in [`SECRET_SCAN.md`](SECRET_SCAN.md) HOLD-1.
2. **Corrected metrics, with sample size.** Once the inverted-probability and ROC-AUC-from-hard-labels defects are fixed and the models retrained, report the figures **with the validation-split row count** so they can be added to the README honestly. Until then the README deliberately quotes none.
3. **`pyproject.toml` is missing its `[project]` table.** `name` and `version` sit as bare top-level keys with no section header. Valid TOML, and `[tool.pytest.ini_options]` still works, so this breaks nothing today — but the file is not a conforming project manifest and `pip install -e .` would fail. Low priority.
4. **Dependency pinning in `requirements.txt`.** Left unedited to avoid colliding with concurrent changes. Must be applied by whoever commits last, before deployment. Specification in [`DEPLOYMENT.md`](DEPLOYMENT.md), Gaps 8 and 9.
