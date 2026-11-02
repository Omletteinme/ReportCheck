# Plain LLM vs best-of-N (heldout, 40 reports)

| metric | plain LLM | best-of-N | difference (95% CI, paired bootstrap) |
|---|---|---|---|
| pass all hard checks | 0.12 | 0.23 | +0.10 (-0.03 to +0.23) |
| meaning (entailment) | 0.85 | 0.91 | +0.05 (+0.00 to +0.10) |
| numbers/sides | 0.87 | 0.96 | +0.09 (+0.03 to +0.16) |
| certainty | 0.73 | 0.94 | +0.21 (+0.12 to +0.30) |
| simplicity | 0.18 | 0.21 | +0.02 (-0.05 to +0.10) |
| verifier total | 0.73 | 0.82 | +0.10 (+0.06 to +0.14) |
| reading grade (FK) | 10.26 | 10.06 | -0.21 (-1.13 to +0.70) |
| word overlap w/ source | 0.33 | 0.44 | +0.11 (+0.05 to +0.18) |

Verifier-based rows are circular for best-of-N (the verifier selects and scores). Labeled rows (if present) were assigned blind by Claude, not humans. Reading grade: lower is easier.
