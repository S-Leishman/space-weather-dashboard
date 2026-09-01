# Submission Checklist — August AI Builders Challenge

**Deadline: 2026-08-31, 11:59 PM ET**
**Compiled:** 2026-08-30 · **Lane:** RELEASE-INFRA-001
**Revised:** 2026-08-31 · **Lane:** SUBMISSION-VET-001 — freeze certification docs to one tip SHA. Row 1 no longer cites the historical 59-test HOLD. Row 11 no longer cites a CI run whose SHA is not the tip.

Every row states a real status backed by an artifact a reader can open. Nothing is marked complete on the assumption that it will be.

**Legend** — `PASS` verified with evidence · `HOLD` blocked or awaiting something named · `HOLD_EVIDENCE` may already be done, but no proof has been supplied · `NOT_STARTED` no work exists yet

## Requirement status

| # | Requirement | Status | Evidence / blocker |
|---|---|---|---|
| 1 | Working prototype | **PASS** | Current tip serves the Streamlit prototype, renders the verified pages, and passes the current 143-test suite. See row 1 detail |
| 2 | IBM SkillsBuild activity completion | **HOLD_EVIDENCE** | **Owner-only.** No completion evidence located. A prior Gmail search found no completion email. Not asserted as done |
| 3 | Public GitHub repository | **PASS** | **PUBLIC** and populated at [`S-Leishman/space-weather-dashboard`](https://github.com/S-Leishman/space-weather-dashboard) — 68 tracked files on `main`. See row 3 detail |
| 4 | README with all required sections | **PASS** | [`README.md`](README.md) — all five sections present. See section map below |
| 5 | Published challenge project page | **NOT_STARTED** | **Owner-only.** Requires the public repository URL (row 3) and the video URL (row 6) |
| 6 | Public video, ≤ 3 minutes | **NOT_STARTED** | **Owner-only.** Not recorded. Out of scope for this lane by instruction |
| 7 | Owner clicks Publish before deadline | **NOT_STARTED** | **Owner-only.** Terminal, irreversible action |
| 8 | License | **PASS** | [`LICENSE`](LICENSE) — MIT, plus a not-for-operational-use notice |
| 9 | Pre-publication secret scan | **PASS** | [`SECRET_SCAN.md`](SECRET_SCAN.md) plus a re-run after the code changes: [`SECRET_SCAN.json`](04_EVIDENCE/lanes/ibm-p0-correctness-001/SECRET_SCAN.json) — 48 text files scanned, `NO_FINDING` |
| 10 | `.gitignore` protecting credentials | **PASS** | [`.gitignore`](.gitignore) — blocks `.env`, keys, `.streamlit/secrets.toml` before any commit exists |
| 11 | CI pipeline | **PASS** | Workflow present and last independently-read green run is [33431949236](https://github.com/S-Leishman/space-weather-dashboard/actions/runs/33431949236) at `76a4fd05`, 143 passed. This freeze SHA's CI is bound in the vet package after independent read-back. See CI section |
| 12 | Public deployment URL | **HOLD** | Scoped in [`DEPLOYMENT.md`](DEPLOYMENT.md), deliberately not executed. Gated on rows 1 and 3 |

### Row 1 detail — working prototype

The software path is verified: the Streamlit app serves HTTP 200 locally, the live NASA DONKI fetch returns data, all three model artifacts load and return probabilities, and 143 of 143 tests pass on the current tip (`python -m pytest -q`).

This PASS status is bounded to the reviewable prototype: CI and the independent browser receipt cover the current tip. It does not imply production deployment, predictive accuracy, or owner publication.

### Row 3 detail — repository state

Resolved. The repository is public, populated, and CI-enabled. Verified 2026-08-31:

```
$ gh repo view S-Leishman/space-weather-dashboard --json visibility,isEmpty
{"visibility":"PUBLIC","isEmpty":false}
```

| | |
|---|---|
| Branch | `main` (matches the `.github/workflows/ci.yml` trigger — see CI-1) |
| Remote `main` tip | this freeze commit (documentation-only); hex bound in the vet package after independent GitHub read-back |
| Files tracked on `main` | 68 · no caches, logs, or credentials |
| Remote | `https://github.com/S-Leishman/space-weather-dashboard` — **PUBLIC, POPULATED** |

**Historical blocker, now cleared.** The first push was rejected because the `gh` token lacked the `workflow` scope and therefore could not create `.github/workflows/ci.yml`:

```
! [remote rejected] HEAD -> main
  (refusing to allow an OAuth App to create or update workflow
   .github/workflows/ci.yml without `workflow` scope)
```

The scope was granted and the push completed. This is retained as a record of what the obstacle was, not as a current status.

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

CI has now executed and is green on `main`. The earlier text in this section said the workflow had never run; that was true when written and is no longer true.

Observed result, not a prediction:

```
$ gh run list --repo S-Leishman/space-weather-dashboard --branch main --limit 1
completed  success  CI  main  33431949236   (head 76a4fd05, pre-freeze)

Last independently-read collection: 143 passed, 0 failed.
This freeze commit is documentation-only. CI on this freeze SHA is not claimed here.
```

| | |
|---|---|
| Last independently-read run | [33431949236](https://github.com/S-Leishman/space-weather-dashboard/actions/runs/33431949236) |
| That run's commit | `76a4fd05cc9e92b31601971f66dbf395d10e0db8` (superseded tip) |
| Result | `success` — 143 passed, 0 failed |
| Freeze tip | this freeze commit — CI rebound in the vet package after independent read |

**Claim ceiling:** this is one green run of the `CI` workflow on `ubuntu-latest`, Python 3.11. It is evidence that the test suite passes in a clean checkout. It is not evidence about hosted runtime behaviour, and CI-2 below (unpinned dependencies) means a future run can go red without a code change.

### CI-1 — Branch trigger mismatch (resolved)

`.github/workflows/ci.yml` triggers on `main` only:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

The hazard was that a `master` default branch would never match this trigger, so CI would report no status at all — which reads as "no tests" to a reviewer, worse than a visible failure.

**Resolved:** the default branch is `main`, it matches the trigger, and run 33431949236 confirmed the workflow fires on the pre-freeze tip.

### CI-2 — Unpinned dependencies make CI non-deterministic

The workflow runs `pip install -r requirements.txt`, where every dependency is `>=`. Two runs a week apart can install different versions, so CI can go red without any code change. The specific hazard is `numpy>=1.26.0` resolving to NumPy 2.x against older `shap`/`scikit-learn` wheels. Detail and fix in [`DEPLOYMENT.md`](DEPLOYMENT.md), Gap 8.

### What CI actually did

This section previously carried a prediction that the job would "probably pass". That prediction has been superseded by an observed result: **143 passed, 0 failed**, run 33431949236 on `76a4fd05`.

One prior divergence is worth recording, because it is the reason CI was red four times today before this run. `dashboard/components/donki_replay.py` anchored its fixture path at `parents[3]`, the parent of the repository. Locally that directory happened to contain `04_EVIDENCE/`, so the suite passed; in a clean CI checkout the path did not exist, so it failed. The fixture is now committed inside the repository and the anchor is `parents[2]`, with a regression test in [`tests/test_donki_replay.py`](tests/test_donki_replay.py) asserting the path stays repo-relative. A local pass is not evidence about a clean clone unless the repository is self-contained.

## Owner-only actions, in order

Only Scott can perform these. Everything up to the irreversible line has been prepared. Estimated hands-on cost: **roughly 20–30 minutes of clicks**, excluding the video recording and the dependency-build wait.

| Step | Action | Why only the owner | Est. |
|---|---|---|---|
| 1 | **Verify IBM SkillsBuild completion** in the SkillsBuild portal; capture a screenshot | Personal account credentials. Hard eligibility gate | 5 min |
| 2 | ~~Grant the `workflow` OAuth scope and push~~ — **DONE.** Scope granted, push completed, repository public and populated | Interactive browser authorization. See row 3 detail | done |
| 3 | **Confirm the application fixes have landed** and an independent verifier reports a correct run | Do not publish a build that renders raw JavaScript | — |
| 4 | **Authorize the re-run secret scan** result (procedure in [`SECRET_SCAN.md`](SECRET_SCAN.md)) | Code changed after the original scan | 2 min |
| 4a | ~~Flip the repository to public~~ — **DONE.** `visibility: PUBLIC`, verified 2026-08-31. This step was irreversible and has been taken | **IRREVERSIBLE, ALREADY EXECUTED** | done |
| 5 | ~~Confirm CI is green on pre-freeze tip~~ — **DONE.** Run 33431949236 on `76a4fd05`, 143 passed. Freeze-SHA CI is rebound in the vet package | Verify before claiming | done |
| 6 | **Deploy to Streamlit Community Cloud** — steps 5–8 of [`DEPLOYMENT.md`](DEPLOYMENT.md) | Requires his GitHub-linked Streamlit account | 10 min + build |
| 7 | **Verify the live URL in a browser** — every page, no raw JavaScript, charts draw, live data returns | This is the last chance to catch a broken public deployment | 5 min |
| 8 | **Record and upload the video**, ≤ 3 minutes, publicly accessible | Requires his voice, screen, and account | 20–30 min |
| 9 | **Publish the challenge project page** with the repository URL and video URL | Requires his challenge-platform account | 10 min |
| 10 | **Click Publish** before 2026-08-31 11:59 PM ET | **TERMINAL AND IRREVERSIBLE** | 1 min |

Steps 1 and 8 are the two that cannot be shortened and do not depend on anything else — they can be done in parallel with the fix work, and doing so is the best use of the remaining time.

## Hard stop — what the RELEASE-INFRA-001 lane did not do, by instruction

Scoped to that lane as of 2026-08-30. The visibility flip and push were performed later by the owner, so the first bullet describes that lane's restraint, not the repository's current state.

- Did **not** change any repository from private to public
- Did **not** deploy to any public URL
- Did **not** publish or submit anything on the challenge platform
- Did **not** record or upload video
- Did **not** force-push or rewrite git history
- Did **not** edit application code (`dashboard/**`, `tests/**`) — owned by the concurrent fix lane

## Hand-offs to the application-fix lane

Items found by this lane that fall inside application-code territory and were **not** touched:

1. **Personal filesystem paths in model metadata.** `dashboard/models/{xgboost,logistic_regression,random_forest}_metadata.json` each carry `"model_file": "<HOME>\\Desktop\\Aevion LLC\\..."`. Not a credential and not a release blocker, but it publishes the owner's username and local directory layout, and the absolute path is unresolvable for anyone who clones the repository. Fix: emit a repository-relative path when writing metadata. Detail in [`SECRET_SCAN.md`](SECRET_SCAN.md) HOLD-1.
2. **Corrected metrics, with sample size.** Once the inverted-probability and ROC-AUC-from-hard-labels defects are fixed and the models retrained, report the figures **with the validation-split row count** so they can be added to the README honestly. Until then the README deliberately quotes none.
3. **`pyproject.toml` is missing its `[project]` table.** `name` and `version` sit as bare top-level keys with no section header. Valid TOML, and `[tool.pytest.ini_options]` still works, so this breaks nothing today — but the file is not a conforming project manifest and `pip install -e .` would fail. Low priority.
4. **Dependency pinning in `requirements.txt`.** Left unedited to avoid colliding with concurrent changes. Must be applied by whoever commits last, before deployment. Specification in [`DEPLOYMENT.md`](DEPLOYMENT.md), Gaps 8 and 9.
