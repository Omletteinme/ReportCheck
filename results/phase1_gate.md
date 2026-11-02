# Phase 1 gate summary (2026-10-21)

| # | Criterion | Result | Status |
|---|---|---|---|
| 1a | >=300 hedged clinical reports | 654 (608 Open-i real + 46 synthetic) | pass |
| 1b | >=150 numeric clinical reports | 191 (141 real + 50 synthetic) | pass, but only 141 are real |
| 2 | Hedge detector precision >=0.85 (50 sentences) | 0.88 (44/50), labeled by Claude | pass, needs human spot-check |
| 3 | Baseline shows measurable error rate | Open-i: 12/20 fabricated/wrong content, 6/20 hedge drift, 4/20 number/laterality; labeled by Claude | pass |
| 4 | >=95% of reports fit 512 tokens | Open-i 100%; PLABA 87.7% | pass (PLABA needs truncation) |

## Findings that change the plan
- **Synthetic reports do not stress numeric fidelity.** The baseline kept 40/40 ground-truth number values.
  Number retention alone is therefore a weak metric. The verifier must check that each number is bound to the
  right finding, and that no unsupported qualifiers are added (e.g. a 5.4 cm thyroid nodule called "small").
- **Real Open-i outputs fail on hedge drift, laterality, and invented content**, so Gaps 1 and 3 have room to show gains.
- **Hedge lexicon fixes for `hedge.py`:** exclude modals inside recommendations ("could be performed",
  "may be warranted") and "consistent with known ..." attribution.
- **Open-i contains `XXXX` anonymization in 51% of reports**; the model sometimes guesses values for it
  (e.g. "7 mm x 7 mm"). The verifier should penalize numbers absent from the source.
- **Hardware:** generation speed depends on the GPU being free (19 tok/s idle vs 2.5 tok/s with a game running).

## Verdict
Go for Phase 2, with the claim that numeric-fidelity results rest partly on synthetic data.
