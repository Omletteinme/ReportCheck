# Verifier tuning summary

All labels (H = hedge shifted/dropped/added, N = number/laterality wrong, F = fabricated or wrong content) were
assigned by Claude, not a human. Test and fresh-set labels were assigned blind to prompt mode and verifier score.
Reproduce: `.venv/Scripts/python scripts/eval_verifier.py`.

## What changed (all in `src/`)
| Change | Evidence |
|---|---|
| Sentence splitter no longer deletes `**Findings:** text` paragraphs (regression test added) | bug hid whole outputs from every earlier score |
| Hedge lexicon: suggest(s/ing/ed), indicative of, potentially, seem(s), likelihood; exclude "no ... to suggest" | certainty AUC vs H 0.57 -> 0.71 on set 1 |
| Certainty also penalises more hedged sentences than the source | same |
| Entailment = best support over whole source and each source sentence (SummaC-style), parenthetical glosses dropped | AUC vs F 0.65 -> 0.77 (dev+test) |
| Facts score also checks laterality and severity words (small/mild/moderate/severe) | catches left/right swaps, "moderate" -> "severe" |
| Structured prompt: no mandatory recommendation paragraph, no added hedging/severity words | fabrication rate on structured outputs 0.85 -> 0.50 |

## Results (pairwise AUC, 0.5 = chance; 95% bootstrap CI)
| Set | n (clean / errored) | total vs any error | certainty vs H | entail vs F |
|---|---|---|---|---|
| Dev (20, used to diagnose) | 7 / 13 | 0.65 (0.36-0.93) | 0.62 | 0.73 |
| Set 1 (40, used to diagnose after first scoring) | 7 / 33 | 0.79 (0.49-1.00) | 0.71 | 0.80 |
| **Set 2 (40, fresh, never used for tuning)** | 14 / 26 | **0.77 (0.60-0.92)** | **0.78** | **0.76** |

First scoring of set 1 with the original verifier was 0.58 total; the fixes above lift the fresh-set figure to 0.77.

## Prompt comparison (error rates among 20 outputs per cell)
| Set | Prompt | H | N | F |
|---|---|---|---|---|
| 1 | baseline | 0.40 | 0.00 | 0.50 |
| 1 | structured (old) | 0.50 | 0.05 | 0.85 |
| 2 | baseline | 0.25 | 0.05 | 0.65 |
| 2 | structured (new) | 0.30 | 0.00 | 0.50 |

The new structured prompt removed the old prompt's fabricated recommendations, but on pooled data it is not
clearly better than the baseline prompt (n = 20 per cell, differences within noise). It also leaks artifacts
(literal "**Likely**" tags, "Unit 10", "Finding 1" headings) despite the instruction. Discourse conditioning
via prompting alone is therefore **not yet shown to help**; that claim should wait for the DPO/best-of-N results.

## Known limits
- Numeric component: only 6 of 100 labeled outputs have a number/laterality error, so its AUC is not meaningful.
  Spelled-out counts without a unit ("Two calcified nodules") are not extracted.
- Facts are not bound to findings; a correct number or side on the wrong finding passes.
- Omission of content (for example a dropped "Probable DISH") is not penalised by any component.
- 1.5B model: ~35-65% of outputs contain some fabricated content even with the better prompt.
