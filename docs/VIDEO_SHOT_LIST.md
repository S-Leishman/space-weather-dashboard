# Aevion SpaceOps — ≤3-Minute Demo Shot List

Bound to the release commit recorded in `IBM-SUBMISSION-CANDIDATE.json`.

**Before you start**

1. `cd space-weather-dashboard`
2. `streamlit run dashboard/app.py` → wait for `http://localhost:8501` to finish its first
   run (HOME performs a live NASA DONKI fetch and takes ~20–40 s to settle).
3. Browser at 1600×1200, zoom 100 %, no bookmarks bar, no notifications.
4. Screenshots for every beat are in `docs/demo/` — use them to rehearse so you can record
   straight through without hunting for anything.

Total narration below runs ~2 min 50 s at a normal speaking pace.

---

## 0:00–0:20 — The problem

**Screen:** HOME (Mission Control), scrolled to the top so the title block and the framing
line are visible.
**Screenshot:** `docs/demo/beat1_problem.png`

> "Space weather can threaten a launch — flares, coronal mass ejections, geomagnetic
> storms. But the hard part isn't getting a prediction. Predictions are cheap now. The hard
> part is that a number on a screen doesn't tell the person who carries the consequences
> whether it's safe to act on it. Which model said this? From what data? Can I reproduce it
> in a review six months from now?"

**Action:** none — hold on the title.

---

## 0:20–0:40 — The product

**Screen:** HOME, scrolled so the **Mission Decision — Evidence Gated** section and the
decision chain strip are both visible.
**Screenshot:** `docs/demo/beat2_product.png`

> "Aevion SpaceOps is an evidence-gated mission decision system. The space-weather model is
> an input — it is not the product. The product is the decision record. Space data, model
> inference, evidence package, provenance, policy check, and then a human mission decision.
> The software never launches, aborts, or authorizes. A person does."

**Action:** slowly move the cursor left-to-right along the decision chain as you name each
stage.

---

## 0:40–1:35 — One live scenario: SPACE DATA → MODEL → RISK → RECEIPT

**Screen:** HOME, the scenario controls in the sidebar plus the verdict panel.
**Screenshots:** `docs/demo/beat3a_inputs.png`, `docs/demo/beat3b_verdict.png`,
`docs/demo/beat3c_receipt.png`

> "Here's one scenario end to end. These are the live inputs — Kp index, F10.7 solar flux,
> storm level, launch hour."

**Action:** drag the **Kp Index** slider up to a stormy value (7+). Let the page re-run.

> "The model scores it. Note the label: Prototype GO Score, and Prototype model score —
> not a launch probability. That wording is deliberate, and I'll come back to why."

**Action:** point at the verdict and the score line.

> "That score then goes through a policy check, and the policy check is gated on evidence,
> not just on the number. You can see the state — PASS, FAIL, HOLD, or UNKNOWN — and every
> reason that produced it."

**Action:** open the **EVIDENCE PACKAGE** expander.

> "And here is the receipt: the model that ran, the SHA-256 of that model artifact, the
> timestamp, the inputs, the result, and a receipt hash computed over the package itself.
> Recompute the hash and you can verify nothing drifted."

---

## 1:35–2:15 — Evidence view, and the authority boundary

**Screen:** Data Pipeline page, then back to HOME's provenance table.
**Screenshots:** `docs/demo/beat4a_pipeline.png`, `docs/demo/beat4b_provenance.png`

**Action:** click **Data Pipeline** in the sidebar.

> "The evidence is addressable, not decorative. The feature artifact carries a SHA-256, a
> row count, and its label semantics. And notice this page is telling you what it does
> *not* have — the raw DONKI pulls aren't committed, so it says MISSING. We didn't hide
> that warning to make the demo look clean. Both pages resolve the same artifact root, and
> the page says so, so you can't mistake it for two pages contradicting each other."

**Action:** return to HOME, scroll to the provenance table.

> "That's the whole posture: AI recommends, human authority decides. A HOLD is a request
> for a human, not a decision. The system's job is to hand a person a record they can
> inspect — not to ask them to trust a gauge."

---

## 2:15–2:40 — How IBM Bob was used

**Screen:** About page, phase log visible.
**Screenshot:** `docs/demo/beat5_bob.png`

**Action:** click **About** in the sidebar.

> "IBM Bob was the primary development tool. The application was built in Bob across seven
> phases — scaffolding, the NASA and NOAA ingestion client, feature engineering, model
> training, the dashboard, the tests and CI, and the multi-page frontend. Every phase is
> logged right here in the app. After that session closed we ran an independent correctness
> pass with separate tooling, and the README says exactly which parts those were. We'd
> rather state the boundary of our evidence than overstate inside it."

---

## 2:40–3:00 — Impact

**Screen:** Model Lab page, showing the synthetic-label candour, then back to HOME.
**Screenshot:** `docs/demo/beat6_impact.png`

**Action:** click **Model Lab**.

> "One last thing, and it's the point. This model's training label is synthetic — it's
> independent of the features — so it has no demonstrated predictive skill, and an AUC near
> 0.5 is the expected result. The app says that out loud instead of hiding it behind a
> confident number. The pipeline is real, the evidence chain is real, the human-authority
> boundary is real. A system that tells you when not to trust it is the entire thesis —
> and that's what makes AI admissible in a mission decision loop."

---

## Recording note

Screen recording is the **owner's step** — this environment has no screen-capture or audio
tooling. Everything else is prepared: the storyboard above, the exact narration, the exact
screen actions in order, and a still for every beat in `docs/demo/`.
