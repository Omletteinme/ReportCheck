# Tables for the paper

All error labels were assigned blind by Claude (an AI), not by humans. CIs are 95% paired bootstrap.

## Table 1. Plain draft vs best-of-N on 120 unseen reports (labeled, independent of the verifier)

| Error | Plain | Best-of-N | Difference (95% CI) |
|---|---|---|---|
| Any error (H, N or F) | 0.81 | 0.68 | -0.12 (-0.21 to -0.04) |
| Unsupported content (F) | 0.70 | 0.59 | -0.11 (-0.20 to -0.02) |
| Hedge level changed (H) | 0.20 | 0.17 | -0.03 (-0.10 to +0.05) |
| Number or side wrong (N) | 0.07 | 0.07 | +0.00 (-0.06 to +0.05) |
| Key finding left out (O) | 0.04 | 0.10 | +0.06 (+0.00 to +0.12) |

Readability (lower reading grade is easier; higher simplicity is simpler):

| Measure | Plain | Best-of-N | Difference (95% CI) |
|---|---|---|---|
| Reading grade (Flesch-Kincaid) | 10.01 | 10.59 | +0.58 (-0.07 to +1.21) |
| Simplicity score | 0.31 | 0.25 | -0.06 (-0.11 to -0.01) |

Verifier-scored rows are circular for best-of-N (the verifier chose the draft), so they are not shown here;
see results/final_summary.md.

## Table 2. Verifier AUC (total score vs any labeled error), before and after the comparison, number-side and omission checks

| Set | n | Before (95% CI) | After (95% CI) |
|---|---|---|---|
| Dev | 20 | 0.68 (0.43-0.93) | 0.67 (0.37-0.97) |
| Set 1 | 40 | 0.79 (0.49-1.00) | 0.81 (0.55-0.98) |
| Set 2 | 40 | 0.77 (0.60-0.92) | 0.77 (0.60-0.92) |
| Set 3 (3B outputs) | 40 | 0.67 (0.48-0.84) | 0.55 (0.34-0.77) |
| Dev + set 1 | 60 | 0.73 (0.52-0.90) | 0.75 (0.53-0.91) |

AUC 0.5 is chance. Set 3 is not used for tuning and its AUC dropped; CIs are wide.

## Table 3. Verifier components on the 120 plain outputs (not circular)

| Score vs label | AUC | Error cases |
|---|---|---|
| total vs any H/N/F error | 0.81 | 97 |
| certainty vs H | 0.69 | 24 |
| numbers vs N | 0.69 | 8 |
| entail vs F | 0.66 | 84 |
| coverage vs O (omission) | 0.75 | 5 |

Omission (coverage vs O) has only 5 error cases: weak evidence.
