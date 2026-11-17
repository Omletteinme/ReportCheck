# T5 hybrid vs earlier systems (120 reports, no labels)

Reading grade is Flesch-Kincaid (lower is easier). The change column is a coarse report-level check, not an error rate. Entailment and coverage come from the verifier that selected best-of-N, so they are circular for that system.

### All 120 reports

| system | reading grade | reports at grade 8 or easier | reports where a number, side, severity, hedge or negation changed | entailment (verifier) | coverage (verifier) |
|---|---|---|---|---|---|
| original | 11.18 | 14% | 0% | 0.99 | 0.99 |
| plain | 10.83 | 18% | 59% | 0.81 | 0.86 |
| best_of_n | 11.35 | 13% | 37% | 0.87 | 0.94 |
| rules | 7.19 | 71% | 0% | 0.90 | 0.87 |
| t5_raw | 6.38 | 84% | 12% | 0.92 | 0.92 |
| hybrid_standard | 6.18 | 85% | 1% | 0.95 | 0.94 |
| hybrid_guard | 6.67 | 78% | 0% | 0.92 | 0.90 |
| hybrid_strict | 7.16 | 71% | 0% | 0.90 | 0.87 |

### Reports that are also in BioLaySumm (never used for training)

| system | reading grade | reports at grade 8 or easier | reports where a number, side, severity, hedge or negation changed | entailment (verifier) | coverage (verifier) |
|---|---|---|---|---|---|
| original | 11.24 | 9% | 0% | 0.99 | 0.99 |
| plain | 10.41 | 21% | 56% | 0.83 | 0.84 |
| best_of_n | 11.20 | 13% | 35% | 0.85 | 0.94 |
| rules | 7.00 | 78% | 0% | 0.89 | 0.90 |
| t5_raw | 6.44 | 90% | 10% | 0.92 | 0.95 |
| hybrid_standard | 6.16 | 91% | 1% | 0.94 | 0.94 |
| hybrid_guard | 6.50 | 82% | 0% | 0.91 | 0.90 |
| hybrid_strict | 6.99 | 78% | 0% | 0.90 | 0.91 |

### Reports that are not in BioLaySumm

| system | reading grade | reports at grade 8 or easier | reports where a number, side, severity, hedge or negation changed | entailment (verifier) | coverage (verifier) |
|---|---|---|---|---|---|
| original | 11.11 | 21% | 0% | 0.98 | 0.99 |
| plain | 11.38 | 13% | 63% | 0.78 | 0.87 |
| best_of_n | 11.54 | 13% | 38% | 0.89 | 0.94 |
| rules | 7.43 | 62% | 0% | 0.90 | 0.83 |
| t5_raw | 6.29 | 77% | 15% | 0.93 | 0.89 |
| hybrid_standard | 6.21 | 77% | 0% | 0.96 | 0.95 |
| hybrid_guard | 6.90 | 73% | 0% | 0.93 | 0.89 |
| hybrid_strict | 7.40 | 62% | 0% | 0.90 | 0.83 |

### hybrid_standard: where each sentence came from

rewritten 487 (52%), kept 233 (25%), rules 221 (23%)

Most common reasons a T5 sentence was not used: text removed in the report (XXXX) (161), already short (124), meaning not supported (49), content dropped (35), not simpler (30), too long (26), certainty changed (9), severity or comparison changed (5)

### hybrid_guard: where each sentence came from

rules 350 (37%), rewritten 310 (33%), kept 281 (30%)

Most common reasons a T5 sentence was not used: medical term changed (214), text removed in the report (XXXX) (161), already short (124), too long (32), not simpler (28), meaning not supported (24), content dropped (14), certainty changed (9)

### hybrid_strict: where each sentence came from

rules 538 (57%), kept 353 (38%), rewritten 50 (5%)

Most common reasons a T5 sentence was not used: dropped word (465), text removed in the report (XXXX) (161), already short (124), too long (39), new word (34), not simpler (21), certainty changed (13), severity or comparison changed (7)
