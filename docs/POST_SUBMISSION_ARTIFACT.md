# Post-submission artifact — receipt banner

**Status:** Added after IBM Builders submission due to a technical glitch at submit time.

## Frozen submission (do not rewrite history)

| Field | Value |
|---|---|
| Tag | `submission-2026-08-31` |
| SHA | `e07a341cd106944f03bc7ef0e075bdf3e5488c31` |
| CI | GitHub Actions run `33458182758` — 143 passed |
| Message | `docs(ibm): restore required submission README and claim ceilings` |

Judges and vet packages should treat **`submission-2026-08-31` @ `e07a341`** as the submitted artifact.

## Post-submission addition (this commit)

A judge-facing **artifact receipt strip** under the hero on Mission Control (HOME):

- MODEL · MODEL SHA · FEATURES SHA · VERIFICATION · RECEIPT SHA
- Values are computed from on-disk artifacts — no hardware attestation claims
- Does not change the authority model (human mission authority remains)

Added because the receipt/provenance treatment was ready locally but did not land on the submission tip before the platform deadline.

## Claim ceiling

- **DO NOT** claim Zymkey, ML-DSA hardware attestation, or CMVP validation in this UI.
- Trajectory / harness / post-crypto work lives in the Aevion estate, not this submission lineage.
