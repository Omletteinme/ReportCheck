# Labeling guidelines (read fully before starting, ~5 minutes)

**Task.** Each row has a clinical radiology report (`clinical_report`) and an AI-written patient version
(`patient_version`). Decide whether the patient version has any of three kinds of error. Fill the three
columns with **1** (yes, error present) or **0** (no). Leave nothing blank. Use `notes` for anything unclear.
There are 36 rows; it takes about 45–60 minutes. **Label alone. Do not discuss rows with teammates until
everyone has finished**, because we measure how much independent labelers agree.

Judge only the *content*. Ignore formatting, headings, repetition, awkward wording and length.
`XXXX` in the report means the original text was removed; the AI must not guess what was there.

## H – certainty changed
1 if the *level of certainty* of a finding is weakened, strengthened, dropped, or added compared with the report.

| Report says | Patient version says | H |
|---|---|---|
| "may represent atelectasis" | "this is atelectasis" | 1 (strengthened) |
| "Probable DISH" | "might be something called DISH, but we're not sure" | 1 (weakened) |
| "cannot be excluded" | "is present" | 1 |
| "No pneumothorax" (definite) | "there might be no pneumothorax" | 1 (hedge added) |
| "consistent with COPD" | "which suggests COPD" | 0 (same strength) |
| "possible pneumonia" | "could be pneumonia" | 0 |

## N – number, size, time or side wrong
1 if a number, measurement, unit, time interval, or **left/right** side in the patient version is wrong,
invented, or contradicts the report. (A missing number alone is not N; mention it in notes.)

| Report says | Patient version says | N |
|---|---|---|
| "blunted on the right" | "on the left" | 1 |
| "short interval follow-up" | "another scan in a few weeks" (invented timeframe) | 1 |
| "6 mm" | "16 mm" | 1 |
| "bilateral" | "both lungs" | 0 |

## F – unsupported or wrong content
1 if the patient version states something the report does not support or that is wrong:
an invented diagnosis, cause, reassurance ("nothing to worry about"), advice or recommendation that is not
in the report, a wrong body location, an added severity word ("small", "severe") the report does not use,
or a wrong explanation of a medical term.

| Report says | Patient version says | F |
|---|---|---|
| (no recommendation) | "No further action is needed" / "see a doctor soon" | 1 |
| "Probable DISH" | "DISH stands for Disc Herniation Syndrome" (wrong; it is a spine-bone condition) | 1 |
| "bihilar prominence" | "bump at the top of the lungs" (wrong place) | 1 |
| "moderate cardiac failure" | "severe cardiac failure" | 1 |
| "diaphragm" | "the diaphragm (the muscle under your lungs)" (correct explanation) | 0 |
| "granuloma" | "a tiny hard lump from an old infection" (reasonable) | 0 |

A correct plain-language explanation of a term is **not** an error. If you are not sure the explanation is
correct, look it up quickly, or mark 1 and say so in notes.

## Clean row
All three columns 0.

## Edge cases
- Left something out? Not an error by itself (write "omits X" in notes if it seems important).
- One row can have several errors; mark each column that applies.
- Mark 1 when in doubt about a clear mismatch with the report; mark 0 when the wording is just different.

## When finished
Save the file as CSV (keep the same filename) and send it to Jeevitesh. Do not edit the first three columns.
