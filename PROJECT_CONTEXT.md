# PROJECT_CONTEXT.md

Single self-contained description of this project, written so a person or an AI that has only this file can understand it. Last updated 2026-11-03 (after the UI redesign, file upload and figures folder). Repo: https://github.com/Omletteinme/ReportCheck (public). `README.md` has setup/run commands only.

**TL;DR.** University NLP course project (4-person student team, RV University, Bengaluru; interim review about 2026-11-04, final deadline first week of December 2026). It turns radiology reports into patient-friendly text with a small *pretrained, unmodified* LLM (Qwen2.5-1.5B-Instruct) and adds an original **verifier** that checks whether a rewrite kept the report's meaning, numbers, left/right sides, severity words, comparisons, level of certainty (hedges such as "possible", "likely") and key content. The verifier picks the best of about 11 drafts ("best-of-N") and drives a local web demo with a 3D body map. **Nothing has been fine-tuned**; a DPO training step was planned and is paused. Runs locally on one RTX 4060 Laptop GPU (8 GB). Every quality label so far was assigned by an AI (Claude), not by humans. Prototype, not a clinical tool.

## 1. Overview
- **Problem.** Patients read raw radiology reports in portals. LLM rewrites can silently change numbers, flip hedges ("may represent" to "is"), swap left/right, drop findings, or invent reassurance and advice. Readability scores, SARI and BLEU do not detect this.
- **Idea** (from the team's IEEE-format literature review, which proposed it as a build plan; the user said the paper itself does not matter): four gaps: (1) uncertainty is detected but not preserved for patients, (2) discourse structure is not used, (3) training rewards wording not meaning, (4) success is measured by readability not comprehension. This repo implements (1) and (2) as rules and prompting, (3) only as a verifier used for selection, and does not implement (4).
- **Honest claim.** "Verifier-guided selection with a pretrained model, evaluated against blind labels assigned by an AI." Not claimed: a trained model, human-validated results, simpler text, patient comprehension.

## 2. Tech stack
- Windows 11, Python 3.11, project venv `.venv` (never the global Python: polluted with TensorFlow/old protobuf).
- torch 2.6.0+cu124, transformers 5.20.2, sentence-transformers, textstat, trimesh (3D build), numpy, pandas, pytest. trl/peft/bitsandbytes installed but unused (training paused).
- Models from Hugging Face, used as downloaded: `Qwen/Qwen2.5-1.5B-Instruct` (generator, fp16, ~3 GB VRAM) and `cross-encoder/nli-deberta-v3-base` (entailment judge). Qwen2.5-3B and nli-deberta-v3-small were used only in experiments.
- Demo: Python stdlib `http.server` + one vanilla HTML/JS page + three.js 0.160.0 and GSAP 3.12.5 (vendored, no CDN). No framework, no database.
- Data on disk as JSONL/CSV. Git repo exists (one branch `main`); no CI or deploy.

## 3. Architecture
```
report text ("FINDINGS: ... IMPRESSION: ...")
  -> discourse.parse_report: units (finding/impression/recommendation, certainty, numbers) + relations
  -> generate.build_prompt (baseline | structured | structured_plain), Qwen2.5-1.5B drafts
  -> bestofn.sample_candidates: per structured mode 1 greedy + 4 samples (T=0.8) = 10, plus the plain baseline draft
  -> verify.Verifier.score(source, draft) = weighted sum of 5 components (below)
  -> bestofn.choose: top draft passing hard checks, else top scorer
  -> demo: explain() flags words/sentences; glossary.annotate adds fixed term explanations (display only)
```
**Verifier components** (each in [0, 1]; `WEIGHTS` in `src/verify.py`):
| component | weight | what it checks |
|---|---|---|
| entail | 0.2975 | mean over output sentences of best NLI support (whole source and each source sentence; parenthetical glosses stripped) |
| numbers | 0.2125 | number/unit F1 (cm normalized to mm) minus 0.25 per unsupported side, 0.125 per missing side, 0.25 per added severity group, **0.25 per comparison the source does not make or with sides swapped, 0.25 per number moved to the other side** |
| certainty | 0.2125 | distinct hedge levels (unlikely < possible < likely < definite) preserved, none added or dropped |
| simplicity | 0.1275 | Flesch-Kincaid gain / 5; 0 for near-copies (word Jaccard > 0.85) or outputs < 0.4x source length |
| coverage | 0.15 | **omission check**: key source sentences (impression, recommendations, and findings that carry a hedge, measurement or severity word; plain normals like "No pneumothorax." excluded) must be entailed by the output (best over whole output, one sentence, or two adjacent sentences) |

`bestofn.acceptable` (hard checks to be chosen): numbers >= 1.0, certainty >= 0.75, entail >= 0.7, simplicity >= 0.1. Coverage is a soft score only because the NLI check is noisy on paraphrases. `preference_pair` needs a chosen/rejected score gap >= 0.10 (DPO data; not generated at scale).

## 4. Directory structure
```
PROJECT_CONTEXT.md, README.md, requirements.txt, pytest.ini, .gitignore
src/        library code (section 5)
scripts/    runnable builders and experiments (24 files)
tests/      pytest suite, 188 passing (2 opt-in model tests skipped)
demo/       server.py, extract.py (uploaded .txt/.docx/.pdf to text), index.html, body3d.js, examples.json (generated), assets/ (anatomy.glb 46 MB, anatomy.json,
            ATTRIBUTION.txt), vendor/ (three.js, GSAP)
data/       reports.jsonl (Open-i, 3,159), plaba.jsonl (749), synthetic.jsonl (50), glossary.csv (95 terms),
            split.json, candidates.jsonl (15 reports, DPO pairs), raw/ (downloads, not in git)
results/    evaluation outputs, labels, summaries, human_labeling/, review/
figures/    images for the paper, report and slides (committed): demo/ screenshots, diagrams/ (SVG+PNG), charts/ (PNG+PDF),
            README.md index with captions and caveats; regenerate with scripts/capture_screenshots.py and scripts/make_figures.py
```
Key results files: `final_eval.jsonl` (240 rows), `final_eval_candidates.jsonl` (every candidate text for the 120 reports), `final_eval_labels.csv` (202 AI labels), `final_summary.md` (table), `verifier_auc_before.txt` / `verifier_auc_after.txt`, `verifier_eval{,2,3}.jsonl` + `_labels.csv`, `human_labeling/` (GUIDELINES.md, MESSAGE.txt, glossary_review.csv, per-teammate sheets; `claude_key.csv` is private and git-ignored), `review/sample_inputs*.md` (demo inputs).

## 5. Key modules (`src/`)
- `text.py` sentence splitting (markdown/section aware). `patterns.py` regexes. `data.py` loaders and `labeled_ids`. `agreement.py` `auc`, `cohen_kappa`, `majority`.
- `hedge.py` 4-level certainty scale; `hedges`, `sentence_certainty` (weakest hedge wins), `certainty_profile`; false-hedge exclusions ("could be performed"); lexicon includes "cannot rule out".
- `numbers.py` `find_facts`/`extract`, `sides` (idioms like "right now" excluded), `qualifier_words`, **`comparisons`** ("left greater than right", direction normalized, glosses skipped), **`wrong_comparisons`**, **`misbound_numbers`** (number tied to a different side than in the source), `compare` returning `{missing, unsupported, wrong_sides, wrong_qualifiers, wrong_comparisons, misbound, score}`. Numbers are still not bound to the specific finding, only to a side.
- `discourse.py` `parse_report` -> `Report(units, edges)`; keeps repeated section labels (a past bug dropped them).
- `generate.py` `Generator` (CUDA required), `build_prompt`. `bestofn.py` `sample_candidates`, `rank`, `acceptable`, `choose`, `preference_pair`, `best_of_n(..., extra=(plain_draft,))`.
- `verify.py` `NliEntailer`, `Verifier` (`support`, `coverage`, `score`, `explain`, `rank`), `key_sentences`, `certainty_score`, `simplicity_score`, `Score(entail, numbers, certainty, simplicity, total, details, coverage)`.
- **`plainrules.py` + `data/plain_rules.csv`** (new, main simplification path): deterministic swaps of medical words and stock phrases for plain wording ("within normal limits" -> "normal", "no acute cardiopulmonary abnormality" -> "no new problem in the heart or lungs", "pleural effusion" -> "fluid around the lungs"), applied in file order (specific rules first). After each sentence is rewritten, `meaning_changes` compares it with the source on numbers, sides, severity group, hedge level and negation; any failure keeps the original sentence. No model, no GPU, instant. The rule table was drafted with AI help and is NOT clinically reviewed. `tests/test_plainrules.py` checks that no rule adds a negation, side, number, hedge or severity word its pattern lacks.
- `sentencewise.py` (experiment, not used by the demo): the LLM rewrites each sentence separately and the rewrite is accepted only if it passes numbers, sides, certainty, negation, added-advice, vocabulary and two-way NLI checks; otherwise the source sentence stays. With strict checks only 2 of 67 sentences (10 reports) were rewritten, with looser checks 12 of 67 but about half were wrong (e.g. "consolidation" -> "thickening", "1.8 cm from the apex" -> "below the costal margin"). Conclusion: Qwen2.5-1.5B cannot rewrite radiology sentences faithfully; kept for the write-up.
- `glossary.py` fixed 95-term plain-language glossary, inserted once per term as "term (explanation)", display-only (never affects scores); a test forbids hedges, sides, severity words and numbers inside explanations.
- `anatomy.py` helpers for the 3D map (`GROUPS` incl. limb bones, `REGION_NODES`, `orientation`, `region_anchors`, `keep_near`).

## 6. Data
- Report record: `{id, source: "openi"|"synthetic", findings, impression, text}`. Open-i = public NLM chest X-ray reports (51% contain `XXXX` anonymization; 19% hedged; 4.5% have a unit measurement). PLABA = 749 abstracts (OSF). **50 synthetic reports** (template-written by our generator, `meta` holds ground truth) are labeled synthetic, used only for unit tests and a smoke run, never in any reported evaluation.
- `split.json`: 645 train / 120 test ids. Reports in labeled evaluation must never enter training (nothing was trained anyway).
- Evaluation sets: verifier sets 1-3 (40 outputs each; set 3 is 3B-model output) with `item,H,N,F,f` labels; **final set** = 40 held-out Open-i test reports + 80 further Open-i reports from the *train* split not in any labeled set (disclose this); each gets a plain draft and a best-of-N pick (240 rows, 202 distinct outputs because 38 picks equal the plain draft).
- Label columns: H hedge/certainty changed, N number/side/time wrong or invented, F unsupported or wrong content (invented diagnosis or reassurance, wrong gloss, wrong location, added severity), f minor gloss slip only (not counted as error), O (final set only) key impression/recommendation left out.

## 7. Interfaces
- Demo server `demo/server.py` at http://localhost:8000: `GET /`, `/api/examples`, `/api/summary` (table from `results/final_summary.md`), `POST /api/extract` (raw file body, `X-Filename` header; returns the text of a .txt/.docx/.pdf, max 5 MB, PDF text layer only), `POST /api/simplify {report}` (rule-based version with per-sentence changes and reading grade before and after; instant, no model), `POST /api/run {report, mode: "quick"|"best"}` (quick about 30 s, best about 2-3 min; one request at a time, 409 if busy). Static `/vendor`, `/assets`, `/body3d.js` are whitelisted with a traversal guard.
- Page: 3D body map (BodyParts3D, CC BY 4.0; full skeleton including limbs; "Chest / Whole body" switch; sentences placed on regions by word rules, so positions are approximate; falls back to a flat SVG without WebGL), "Patient version / Original report" switch for what is placed on the map, callout cards with leader lines. Right column: report box (examples, paste, or upload .txt/.docx/.pdf), **Simplify (instant, rule-based)**, Quick check / Best of 8, then an output card with tabs (**Simplified** (default), Checked draft, Plain draft, Original; the findings explorer is hidden on the Simplified tab because it describes the AI drafts) showing highlighted flags (wrong number, wrong side, number on wrong side, added severity, added comparison, hedge changed, unsupported, "may be left out") with score bars, and a findings explorer (filter chips, prev/next, one statement at a time). Light mode only; animated header; glossary toggle; 120-report comparison table. The earlier score cards and side-by-side comparison were removed, and the page no longer states that the model is pretrained, so slides must say so.
- Scripts (all via `.venv/Scripts/python`): `eval_bestofn.py --reports final [--rescore | --show A B | --score | --limit N]`, `eval_verifier.py`, `build_demo.py`, `build_anatomy.py`, `fetch_vendor.py`, `make_sample_inputs.py`, `make_label_sheets.py`, `capture_screenshots.py` and `make_figures.py` (need `requirements-figures.txt`: playwright, matplotlib; see figures/README.md), `score_human_labels.py`, `build_pairs.py` (paused), data builders (`get_data`, `get_plaba`, `make_synthetic`, `make_split`). `--rescore` re-picks outputs from cached candidates with the current verifier (no generation).

## 8. Setup, run, test
```
python -m venv .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cu124
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest -q                       # 188 passed, 2 skipped
.venv/Scripts/python demo/server.py                     # then open http://localhost:8000
.venv/Scripts/python scripts/eval_bestofn.py --reports final           # GPU, resumable, ~50-120 s/report
.venv/Scripts/python scripts/eval_bestofn.py --reports final --score   # needs results/final_eval_labels.csv
```
Raw data and the 62 MB BodyParts3D archive are not in git; see README for download and rebuild steps. Env: `USE_TF=0` is set in code; `RUN_NLI=1` / `RUN_GPU=1` enable model-loading tests. Do not game on the GPU during runs (laptop RTX 4060, throttles near 85 C). Start long jobs detached; the demo server has exited on its own several times (cause unknown), restart if the page does not load.

## 9. Results (all labels by Claude, blind to system and scores, not human)
**Final evaluation, 120 unseen Open-i reports, plain LLM vs best-of-N** (`results/final_summary.md`):
| metric | plain | best-of-N | difference (95% CI) |
|---|---|---|---|
| any labeled error (H/N/F) | 0.81 | 0.68 | -0.12 (-0.21 to -0.04) |
| unsupported content (F) | 0.70 | 0.59 | -0.11 (-0.20 to -0.02) |
| hedge error (H) | 0.20 | 0.17 | -0.03 (-0.10 to +0.05) |
| number/side error (N) | 0.07 | 0.07 | +0.00 (-0.06 to +0.05) |
| key finding left out (O) | 0.04 | 0.10 | +0.06 (+0.00 to +0.12) |
| reading grade (FK, lower easier) | 10.01 | 10.59 | +0.58 (-0.07 to +1.21) |
| simplicity score | 0.31 | 0.25 | -0.06 (-0.11 to -0.01) |
| pass all hard checks (verifier, circular) | 0.11 | 0.23 | +0.12 (+0.07 to +0.17) |
| verifier total (circular) | 0.73 | 0.82 | +0.09 (+0.07 to +0.11) |
Reading: best-of-N reduces unsupported content and the overall error rate, does not significantly change hedge or number errors, **does not make text simpler** (reading grade about 10 for both), and may drop key content slightly more often. Even the selected outputs have labeled errors in 68% of cases (strict labeling; most F cases are wrong or invented glosses and reassurance). Verifier-based rows are circular for best-of-N because the verifier both selects and scores.

**Rule-based simplification** (`plainrules.py`, measured with textstat, no labels needed for reading grade): on the same 120 reports the average Flesch-Kincaid grade is original 11.18, plain AI draft 10.83, best-of-N 11.35, **rules 7.37**; the share of reports at grade 8 or easier is 14% / 18% / 13% / **68%**. 577 of 941 sentences (61%) were reworded and none needed the fallback. Across all 3,159 Open-i reports the mean grade falls from 11.45 to 5.47. These rewrites have NOT been labeled for errors: the swaps are deterministic and meaning-checked (numbers, sides, severity, hedge, negation) but the plain wordings themselves (for example "air leak around the lung" for pneumothorax) need clinician or teammate review before any claim of correctness.

**Verifier AUC** (0.5 = chance; P(clean output scores above errored one)), before -> after the comparison, side-binding and coverage changes, total vs any error: dev 0.68 -> 0.67 (n=20), set 1 0.79 -> 0.81, set 2 0.77 -> 0.77 (fresh, CI 0.60-0.92), set 3 (3B outputs) 0.67 -> **0.55** (CI 0.34-0.77, worse), combined dev+test 0.73 -> 0.75. On the 120 *plain* final outputs (not circular): total vs any error 0.81, certainty vs H 0.69, numbers vs N 0.69, entail vs F 0.66, coverage vs O 0.75 (only 5 positives). Confidence intervals are wide; clean examples are scarce (23 of 120 plain outputs had no labeled error).

Other findings: the 1.5B model is faithful mainly when it stays close to the source; strong "12-year-old" prompts made it invent content; the 3B model reads at grade ~5 but fabricates in over half its outputs. Earlier 40-report held-out run (verifier-scored only) is superseded by the final set.

## 10. Known weaknesses
Verifier: NLI is noisy on paraphrase and negation (coverage misses "pleuritis" vs "pleurisy"; entailment can pass a changed meaning); numbers are tied to a side but not to a specific finding; spelled counts without units ("Two nodules") are missed; N-type errors are rare (about 7%), so that component is barely validated; set 3 AUC fell after the latest changes. Generation: outputs are often near-copies of the source with markdown headings; glosses are frequently wrong (e.g., pneumothorax described as fluid) or add reassurance ("nothing to worry about"); the model guesses text hidden as `XXXX`. Evidence: labels are AI-assigned and strict; 80 of the 120 reports come from the train split; 50 synthetic reports excluded from results; no patient-comprehension test.

## 11. Pending / next steps
- **Main focus is now simplification.** Next: have a teammate or clinician review `data/plain_rules.csv`; label the rule-based outputs for the 120 reports (not done, needs the user's go-ahead) and re-run the comparison; feed the simplified text into the 3D map and findings explorer (they still use the AI drafts); extend the rule table where the 120-report sample still reads hard (rare findings, devices, "XXXX" sentences are left as written).
- Teammate human labels and the glossary review (labeling package in `results/human_labeling/`; user said they cannot collect these for now). Do not present AI labels as human.
- Slide outline `results/review/SLIDES.md` not written. Final write-up needs the framing in section 1 and the caveats in section 10.
- Optional: comprehension-question evaluation, DPO pairs (only 15 of 645 train reports have candidates), a stronger generator, fixing glossary wording errors in model output, hard coverage threshold if NLI noise is reduced.

## 12. Rules and constraints
- Do not claim a trained model, do not present synthetic reports as real, do not present AI labels as human labels. Do not change `data/split.json` or labeled files. Keep `results/human_labeling/claude_key.csv` private until teammates finish.
- 8 GB VRAM, slow internet, deadline first week of December 2026. Never use the global Python.
- Code conventions: plain Python 3.11, type hints, short docstrings stating the why, one test file per module, injected `entail_fn` so tests run without models. Edit files with the editor tools, not shell heredocs (escape characters get corrupted).
- Credits: Open-i (NLM), PLABA, BodyParts3D (CC BY 4.0, credit shown on the page), three.js, GSAP.

## 13. How to help me
You are helping with the project above. Ask for specific files or snippets rather than assuming (module names are in section 5). Match existing conventions, give complete working code and name the file it belongs in, run commands with `.venv/Scripts/python` on Windows. Be honest about limits: if a result is weak or a claim unsupported, say so instead of polishing it. Never suggest faking results, models or labels; suggest honest framings. Prefer changes that run on an 8 GB GPU and a slow connection.
