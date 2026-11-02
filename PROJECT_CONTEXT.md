# PROJECT_CONTEXT.md

**TL;DR.** University NLP course project (4-person student team, RV University, Bengaluru; final deadline first week of Dec 2026, an interim review about 2026-11-04). It turns radiology reports into patient-friendly text with a small *pretrained, unmodified* LLM (Qwen2.5-1.5B-Instruct) and adds an original **verifier** that checks whether each rewrite kept the report's meaning, numbers, left/right sides, severity words and level of certainty (hedges like "possible", "likely"). The verifier is used to pick the best of ~11 drafts ("best-of-N") and drives a local web demo. Nothing has been fine-tuned; a DPO training step (preference pairs ranked by the verifier) was planned but is paused. Everything runs locally on one RTX 4060 Laptop GPU (8 GB). All quality labels so far were assigned by an AI (Claude), not humans; human labeling by teammates is pending. No git repo, no CI/deploy.

## 1. Overview
- **Problem.** Patients read raw radiology reports in online portals. LLM rewrites can silently change numbers, flip hedges ("may represent" -> "is"), swap left/right, or invent reassurance/advice. Common metrics (readability grade, SARI, BLEU) do not detect this.
- **Idea (from the team's IEEE-format literature review, which proposed it as a build plan).** Four gaps: (1) uncertainty is detected but not preserved/calibrated for patients, (2) discourse structure is not used to condition generation, (3) training rewards wording not meaning, (4) success is measured by readability, not comprehension. This repo implements (1) and (2) as rules/prompting, (3) only as a verifier used for selection (training not done), and has not implemented (4).
- **Audience.** Course reviewers; the code is a research prototype, not a clinical tool.
- **Maturity (2026-10-29).** Working pipeline + demo + tests (72 pass, 2 opt-in skipped). Evaluation evidence is small and AI-labeled. Not validated clinically.

## 2. Tech stack
- Windows 11, Python 3.11.9, project venv `.venv` (do not use global Python: it is polluted with TensorFlow/old protobuf).
- torch 2.6.0+cu124, transformers 5.20.2, trl 1.16.0, peft 0.21.2, accelerate 1.15.0, bitsandbytes 0.50.2, datasets 5.1.0, sentence-transformers 6.2.0, textstat 0.7.13, numpy 2.4.6, pandas 3.0.6, hf-xet 1.7.0, pytest 9.1.1. (trl/peft/bitsandbytes are installed but unused so far.)
- Models (Hugging Face Hub, used as downloaded): `Qwen/Qwen2.5-1.5B-Instruct` (generator, fp16, ~3 GB VRAM), `cross-encoder/nli-deberta-v3-base` (entailment judge). `Qwen/Qwen2.5-3B-Instruct` and `cross-encoder/nli-deberta-v3-small` were used only in experiments.
- Demo: Python stdlib `http.server` + one vanilla HTML/JS file. No web framework, no database.
- Data: JSONL/CSV files on disk.

## 3. Architecture
```
report text ("FINDINGS: ... IMPRESSION: ...")
   |
   v
discourse.parse_report -> Units (role: finding/impression/recommendation,
                         certainty level, numbers) + relations (summarizes, motivated_by)
   |
   v
generate.build_prompt (modes: baseline | structured | structured_plain)
   |                                     Generator (Qwen2.5-1.5B) samples drafts
   v
bestofn.sample_candidates: per structured mode 1 greedy + 4 samples (T=0.8) = 10, plus the plain draft
   |
   v
verify.Verifier.score(source, draft) = 0.35*entail + 0.25*numbers + 0.25*certainty + 0.15*simplicity
   |
   v
bestofn.choose: top draft passing hard checks, else top scorer
   |
   v
demo: explain() flags words/sentences; glossary.annotate adds fixed term explanations (display only)
```
Offline evaluation: labeled output sets -> `scripts/eval_verifier.py` (AUC), plain-vs-best-of-N on held-out reports -> `scripts/eval_bestofn.py`.

## 4. Directory structure
```
PROJECT_CONTEXT.md        this file
README.md                 setup/run commands (partly stale on eval_bestofn defaults)
requirements.txt, pytest.ini
src/                      library code (see section 5)
scripts/                  runnable experiments/builders (19 files)
tests/                    pytest suite, one file per src module
demo/                     server.py, index.html, body3d.js (3D viewer), examples.json (generated),
                          assets/ (anatomy.glb 43 MB, anatomy.json, ATTRIBUTION.txt), vendor/ (three.js 0.160.0, GSAP 3.12.5)
data/                     reports.jsonl (Open-i), plaba.jsonl, synthetic.jsonl, glossary.csv,
                          split.json, candidates.jsonl (15 reports), raw/ (downloads)
results/                  labeled outputs, labels, summaries, human_labeling/, review/
.venv/                    virtual environment
```
Key results files: `results/verifier_tuning_summary.md`, `phase1_gate.md`, `heldout_summary.md`, `verifier_eval{,2,3}.jsonl` + `_labels.csv`, `human_labeling/` (guidelines, sheets, private `claude_key.csv`).

## 5. Key modules (`src/`)
- `text.py`: `split_sentences` (markdown/section-aware), `strip_markdown`.
- `patterns.py`: regexes for hedges, numbers, recommendations, normal reports (used by data scripts).
- `hedge.py`: 4-level certainty scale `unlikely < possible < likely < definite`; `hedges`, `sentence_certainty` (weakest hedge wins), `certainty_profile`; `_EXCLUDE_RE` removes false hedges ("could be performed", "consistent with known ..."); works on clinical and patient wording.
- `numbers.py`: `find_facts`/`extract` (value+unit, cm normalized to mm, number words), `side_words`/`sides` (left/right/bilateral/both; idioms like "right now" excluded), `qualifier_words` (low/mid/high severity groups, negations ignored), `compare(source, output)` -> `{missing, unsupported, wrong_sides, wrong_qualifiers, score}`; score = number F1 minus 0.25 per wrong side, 0.125 per missing side, 0.25 per added severity group. Not bound to findings (a correct number on the wrong finding passes).
- `discourse.py`: `parse_report` -> `Report(units, edges)`; `Unit(id, role, text, certainty, numbers)`; rule-based.
- `generate.py`: `Generator(model_id).generate(prompt, n, temperature, max_new_tokens)` (lazy load, CUDA required), `build_prompt`, `structured_prompt`, `BASELINE_PROMPT`, `PATIENT_PHRASE` tags.
- `verify.py`: `NliEntailer` (DeBERTa), `Verifier` with `support` (per-sentence max entailment over whole source and each source sentence; parenthetical glosses removed), `entailment`, `score` -> `Score(entail, numbers, certainty, simplicity, total)`, `explain` (per-sentence flags: unsupported / wrong number / wrong side / added severity / hedge changed), `rank`. `certainty_score` compares sets of hedge levels; `simplicity_score` uses Flesch-Kincaid gain /5, 0 for near-copies (word Jaccard > 0.85) or outputs < 0.4x source length. Constants: `WEIGHTS`, `SUPPORT_FLAG=0.5`, `NLI_MODEL`.
- `bestofn.py`: `sample_candidates`, `rank`, `acceptable` (numbers >= 1.0, certainty >= 0.75, entail >= 0.7, simplicity >= 0.1), `choose`, `preference_pair` (chosen acceptable best vs worst, gap >= 0.10), `best_of_n(..., extra=(plain_draft,))`, `looks_truncated`.
- `glossary.py`: `load`, `gloss_sentences`, `gloss`, `annotate`; fixed plain-language explanations for 95 terms from `data/glossary.csv`, inserted once per term as "term (explanation)"; display-only.
- `data.py`: `load_reports`, `load_split`, `labeled_ids`. `agreement.py`: `auc`, `cohen_kappa`, `majority`.

## 6. Data models
- Report record (JSONL): `{id, source: "openi"|"synthetic", findings, impression, text}`; PLABA: `{id, source:"plaba", title, text, reference}`; synthetic adds `meta{numbers, certainty, followup}`.
- `data/split.json`: `{train: [645 ids], test: [120 ids]}`. Test = 60 reports used in labeled evaluation + 40 held-out Open-i + 20 synthetic (`synth_030-049`); train = other eligible Open-i + `synth_000-029`. Labeled-evaluation reports must never enter training.
- `candidates.jsonl`: `{id, source, candidates:[{text, entail, numbers, certainty, simplicity, total}]}`; `pairs.jsonl` (`id, prompt, chosen, rejected, scores`) is produced by `build_pairs.py` but **does not exist yet**.
- Labeled output sets: `{item, report_id, mode, source, output}` + labels CSV `item,H,N,F,f` (H hedge changed, N number/side wrong, F unsupported/wrong content, f minor gloss).
- `explain()` JSON (demo): `{score, sentences[{text, support, level, hedge_terms, flags[{kind, terms}], parts, gloss_terms}], source_sentences, summary{...}}`.
- Data facts: 3,159 Open-i reports (public NLM IU X-ray; 51% contain `XXXX` anonymization; 19% hedged; only 4.5% have a unit measurement), 749 PLABA abstracts, 50 synthetic template reports (must be called synthetic).

## 7. APIs and interfaces
- Demo server (`demo/server.py`, `http://localhost:8000`): `GET /`, `GET /api/examples`, `GET /api/summary`, `POST /api/run {report, mode: "quick"|"best"}` (quick = baseline + structured draft, ~30 s; best = best-of-10 + plain draft, ~2-3 min; one request at a time, 409 if busy, report <= 3000 chars). Model loads on first live request.
- Page: a 3D body map (real BodyParts3D anatomy, CC BY 4.0, rendered with three.js; markers are HTML buttons projected from 3D anchors; clicking a marker glides the camera there with GSAP and highlights the organ; one label shown at a time; falls back to a flat SVG figure if the model/WebGL is unavailable), a findings list, score cards, three comparison columns (original, plain LLM, verifier-selected) with highlighted flags and score bars, "Explain medical terms" checkbox, held-out table footer. Static routes `/vendor/...`, `/assets/...`, `/body3d.js` are whitelisted by extension with a path-traversal guard (`static_file`).
- 3D assets: `scripts/fetch_vendor.py` (libraries), `scripts/build_anatomy.py` (BodyParts3D archive -> `anatomy.glb` + per-region anchors; helpers in `src/anatomy.py`: `select_parts`, `orientation`, `region_anchors`, `keep_near`). BodyParts3D lungs are airway trees only, so lobe shells (smoothed convex hulls) are added. The archive (62 MB) is not in the repo; see README.
- CLI scripts (all use `.venv/Scripts/python`): `make_split.py`, `build_pairs.py [--limit N --n 8 --pairs-only]`, `eval_bestofn.py [--reports heldout|set2] [--show A B | --score]`, `eval_verifier.py`, `build_demo.py`, `score_human_labels.py`, `make_label_sheets.py`, `make_glossary_review.py`, `glossary_coverage.py`, `data_check.py`, `smoke_baseline.py`, `vram_test.py`, others in `scripts/`.

## 8. Configuration and environment
- No config files, secrets, or API keys. Env vars: `USE_TF=0` (set automatically in code to avoid a TensorFlow/protobuf clash), `RUN_NLI=1` and `RUN_GPU=1` (opt-in tests that load models).
- External: Hugging Face Hub (model downloads, large; connection can be slow, `hf_xet` helps), NLM Open-i archive `openi.nlm.nih.gov/imgs/collections/NLMCXR_reports.tgz` (public), PLABA on OSF `osf.io/rnpmf` (public).
- Hardware: RTX 4060 Laptop 8 GB; generation ~19 tok/s when GPU is free, ~10x slower if a game uses it; laptop throttles near 85 C.

## 9. Setup, run, test
```
python -m venv .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cu124
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest -q                              # 72 passed, 2 skipped
RUN_NLI=1 RUN_GPU=1 .venv/Scripts/python -m pytest -q          # also loads models
.venv/Scripts/python scripts/eval_bestofn.py --reports heldout        # GPU, resumable, ~1 min/report
.venv/Scripts/python scripts/eval_bestofn.py --reports heldout --score
.venv/Scripts/python scripts/build_demo.py && .venv/Scripts/python demo/server.py
```
Rebuild data: download/extract Open-i to `data/raw/openi_xml/`, PLABA `data.json` to `data/raw/plaba/`, then `get_data.py`, `get_plaba.py`, `make_synthetic.py`, `make_split.py`. No build/deploy step.

## 10. Conventions and quirks
- Rules + small models, no training. Plain Python, type hints, short docstrings stating the why; tests mirror modules; model-loading tests are opt-in. Injected `entail_fn` lets tests run without models.
- Scripts append results and are resumable (`candidates.jsonl`, `heldout_eval.jsonl`).
- Labeling is blind: outputs are shuffled and the prompt mode hidden (`--show A B`).
- Traps: always use `.venv` Python; close games before GPU runs; Windows console shows mojibake for some characters; do not edit the server and expect a running process to change (restart it); glossary explanations must not contain hedges, sides, severity words or numbers (a test enforces this).

## 11. Current state of work
- **Done:** data prep and gate; hedge/number/side/discourse/verifier/best-of-N modules; glossary; demo; labeling package; held-out generation (40 reports x plain vs best-of-N).
- **Findings.** Verifier separates clean from errored outputs (AUC, 0.5 = chance): 0.65 (dev, n=20), 0.79 (set 1), 0.77 (set 2, CI 0.60-0.92, fresh), 0.64 (set 3, 3B-model outputs, CI 0.46-0.81); hedge check ~chance on heavily paraphrased text. 1.5B model is faithful only when it stays close to the source (reading grade ~10-12); strong "simplify" prompts (e.g. "12-year-old") made it invent content; 3B writes grade ~5 text but fabricates in >50% of outputs. Best-of-N tends to select near-copies, hence the simplicity floor.
- **Held-out (40 reports, verifier-scored, circular for best-of-N):** pass-all-hard-checks 0.12 -> 0.23; meaning 0.85 -> 0.91; numbers/sides 0.87 -> 0.96; certainty 0.73 -> 0.94; verifier total 0.73 -> 0.82; reading grade 10.3 -> 10.1 (no real simplification gain); word overlap with source 0.33 -> 0.44. Blind labeled error rates for these 80 outputs are **not done yet**.
- **Known failures.** The verifier can miss meaning changes (example: "left greater than right ... scarring" rewritten as "left lung appears larger than the right lung" scored 0.96 meaning). Numbers are not bound to findings; omissions are not penalized; spelled counts without units ("Two nodules") are missed; 7 of 140 labeled outputs have number/side errors so that component is barely validated.
- **Pending/incomplete:** teammate human labels and glossary review; comprehension-question evaluation (the paper's primary metric) not built; `train_dpo.py` not written; `pairs.jsonl` not generated (15 of 645 reports have candidates); README partly stale; slide outline not written.

## 12. Open questions and constraints
- Does the course require actual training (DPO)? Unknown; decides whether the paused pair build/training resumes. Without training the honest claim is "verifier-guided selection with a pretrained model".
- Do not claim a trained model, do not present synthetic reports as real, do not present AI labels as human labels. Do not change `split.json` or labeled files (evaluation integrity); keep `results/human_labeling/claude_key.csv` private until teammates finish.
- Constraints: 8 GB VRAM (3B fp16 barely fits), slow internet, deadline first week Dec 2026.
- Possible next steps: blind-label the 80 held-out outputs, collect human labels, flag comparison phrases ("larger than") that differ from the source, stronger/larger generator plus verifier retuned for lay text, build comprehension questions.

## 13. How to help me
You are helping with the project described above. I cannot paste the whole repo; ask for specific files or snippets (module names are in section 5). Match the existing conventions: plain Python 3.11, type hints, small functions, tests next to each module, commands run with `.venv/Scripts/python` on Windows. Give complete, working code and say which file it belongs in. Be honest about limits: if a result is weak or a claim is unsupported, say so rather than polishing it. Never suggest faking results, models or labels; suggest honest framings instead. Prefer changes that run on an 8 GB GPU and a slow connection.
