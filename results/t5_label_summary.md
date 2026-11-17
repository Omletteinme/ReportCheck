# Labeled error rates, 120 reports (labels assigned blind by Claude, an AI, not by humans)

| error | plain | best_of_n | rules | hybrid_guard | hybrid_guard minus plain (95% CI) | hybrid_guard minus best_of_n (95% CI) |
|---|---|---|---|---|---|---|
| any error (H, N or F) | 0.81 | 0.68 | 0.01 | 0.23 | -0.57 (-0.68 to -0.47) | -0.45 (-0.57 to -0.33) |
| unsupported or wrong content (F) | 0.70 | 0.59 | 0.01 | 0.23 | -0.47 (-0.57 to -0.35) | -0.36 (-0.47 to -0.24) |
| hedge level changed (H) | 0.20 | 0.17 | 0.00 | 0.02 | -0.18 (-0.26 to -0.11) | -0.16 (-0.23 to -0.08) |
| number or side wrong (N) | 0.07 | 0.07 | 0.00 | 0.00 | -0.07 (-0.12 to -0.03) | -0.07 (-0.12 to -0.03) |
| key finding left out (O) | 0.04 | 0.10 | 0.00 | 0.00 | -0.04 (-0.08 to -0.01) | -0.10 (-0.16 to -0.05) |
| minor gloss slip only (f, not an error) | 0.10 | 0.07 | 0.06 | 0.12 | +0.02 (-0.06 to +0.09) | +0.04 (-0.03 to +0.11) |

## Labeler consistency on 30 control items (the same outputs labeled earlier and again here)

| label | agreement | Cohen's kappa |
|---|---|---|
| H | 87% | 0.52 |
| N | 97% | 0.78 |
| F | 90% | 0.62 |
| O | 93% | 0.76 |

Treat these as AI-labeled, exploratory numbers: one labeler, no clinician, and the control items show how stable it is.
