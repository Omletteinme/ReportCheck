# Plain LLM vs best-of-N (final, 120 reports)

| metric | plain LLM | best-of-N | difference (95% CI, paired bootstrap) |
|---|---|---|---|
| pass all hard checks | 0.11 | 0.23 | +0.12 (+0.07 to +0.17) |
| meaning (entailment) | 0.81 | 0.87 | +0.06 (+0.03 to +0.09) |
| numbers/sides | 0.87 | 0.95 | +0.08 (+0.05 to +0.12) |
| certainty | 0.66 | 0.89 | +0.23 (+0.17 to +0.29) |
| simplicity | 0.31 | 0.25 | -0.06 (-0.11 to -0.01) |
| nothing left out (coverage) | 0.86 | 0.94 | +0.08 (+0.04 to +0.12) |
| verifier total | 0.73 | 0.82 | +0.09 (+0.07 to +0.11) |
| reading grade (FK) | 10.01 | 10.59 | +0.58 (-0.07 to +1.21) |
| word overlap w/ source | 0.32 | 0.41 | +0.09 (+0.06 to +0.12) |
| hedge error (labeled) | 0.20 | 0.17 | -0.03 (-0.10 to +0.05) |
| number/side error (labeled) | 0.07 | 0.07 | +0.00 (-0.06 to +0.05) |
| unsupported content (labeled) | 0.70 | 0.59 | -0.11 (-0.20 to -0.02) |
| key finding left out (labeled) | 0.04 | 0.10 | +0.06 (+0.00 to +0.12) |
| any error H/N/F (labeled) | 0.81 | 0.68 | -0.12 (-0.21 to -0.04) |

## Verifier AUC on the 120 plain outputs (not circular; 0.5 = chance)

| score vs label | AUC | positives |
|---|---|---|
| total vs any H/N/F error | 0.81 | 97 |
| certainty vs H | 0.69 | 24 |
| numbers vs N | 0.69 | 8 |
| entail vs F | 0.66 | 84 |
| coverage vs O (omission) | 0.75 | 5 |

Verifier-based rows are circular for best-of-N (the verifier selects and scores). Labeled rows (if present) were assigned blind by Claude (an AI), not by humans. Reading grade: lower is easier.
