# Side by side: the paper's systems and the new ones (120 evaluation reports)

Error rows are blind AI labels (Claude, not humans); lower is better. Reading grade is Flesch-Kincaid, lower is easier. Simplicity score: higher is simpler. Verifier total is circular for best-of-N, so do not read it as quality.

| metric | Plain AI draft (paper) | Best-of-N (paper) | Rules only | T5 hybrid (with guard) |
|---|---|---|---|---|
| Any H/N/F error | 0.81 | 0.68 | 0.01 | 0.23 |
| Unsupported content (F) | 0.70 | 0.59 | 0.01 | 0.23 |
| Hedge error (H) | 0.20 | 0.17 | 0.00 | 0.02 |
| Number/side error (N) | 0.07 | 0.07 | 0.00 | 0.00 |
| Key finding omitted (O) | 0.04 | 0.10 | 0.00 | 0.00 |
| Flesch-Kincaid grade | 10.01 | 10.59 | 7.19 | 6.67 |
| Reports at grade 8 or easier | 27% | 16% | 71% | 78% |
| Simplicity score | 0.31 | 0.25 | 0.72 | 0.81 |
| Verifier total (circular for best-of-N) | 0.73 | 0.82 | 0.91 | 0.94 |

The first two columns are Table II of the paper (the same numbers, recomputed). The last two are new and were not in the paper. One AI labeler, no clinician; the rule table has not been clinically reviewed; the T5 model was trained on AI-written plain-language text with no stated licence.
