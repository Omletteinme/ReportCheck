# Plain LLM vs best-of-N (final, 120 reports)

| metric | plain LLM | best-of-N | difference (95% CI, paired bootstrap) |
|---|---|---|---|
| pass all hard checks | 0.12 | 0.25 | +0.12 (+0.07 to +0.19) |
| meaning (entailment) | 0.81 | 0.86 | +0.06 (+0.03 to +0.09) |
| numbers/sides | 0.90 | 0.97 | +0.07 (+0.04 to +0.11) |
| certainty | 0.66 | 0.89 | +0.23 (+0.17 to +0.29) |
| simplicity | 0.31 | 0.29 | -0.02 (-0.07 to +0.03) |
| verifier total | 0.72 | 0.81 | +0.09 (+0.07 to +0.11) |
| reading grade (FK) | 10.01 | 10.26 | +0.26 (-0.51 to +0.95) |
| word overlap w/ source | 0.32 | 0.39 | +0.07 (+0.04 to +0.11) |

Verifier-based rows are circular for best-of-N (the verifier selects and scores). Labeled rows (if present) were assigned blind by Claude, not humans. Reading grade: lower is easier.
