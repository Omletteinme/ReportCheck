# Clinical Report Simplification (NLP project)

Discourse-anchored, verifier-guided simplification of radiology reports.

**Full project context (what it is, how it works, results, limits) is in [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md). This file lists setup and run commands.**
See the IEEE review paper for motivation (Gaps 1-4).

## Layout
- `data/`     reports, preference pairs
- `src/`      text, hedge (certainty scale), numbers, discourse, generate, verify
- `tests/`    pytest suite (RUN_NLI=1 / RUN_GPU=1 enable the model-loading tests)
- `scripts/`  runnable experiments (`vram_test.py` = GPU sanity check)
- `results/`  metrics, outputs

## Setup
    python -m venv .venv
    .venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cu124
    .venv/Scripts/python -m pip install -r requirements.txt
    .venv/Scripts/python scripts/vram_test.py

## Phase 1 (data gate)
Download https://openi.nlm.nih.gov/imgs/collections/NLMCXR_reports.tgz and extract to `data/raw/openi_xml/`, then:

    .venv/Scripts/python scripts/get_data.py          # data/reports.jsonl (openi, real)
    .venv/Scripts/python scripts/get_plaba.py         # data/plaba.jsonl (needs data/raw/plaba/data.json from https://osf.io/rnpmf/)
    .venv/Scripts/python scripts/make_synthetic.py    # data/synthetic.jsonl (50 SYNTHETIC reports, label as synthetic in paper)
    .venv/Scripts/python scripts/data_check.py        # results/data_check.md
    .venv/Scripts/python scripts/make_hedge_sheet.py  # label results/hedge_precision.csv, then --score
    .venv/Scripts/python scripts/smoke_baseline.py    # label results/smoke_baseline.md

## Phase 2
    .venv/Scripts/python -m pytest -q
    RUN_NLI=1 RUN_GPU=1 .venv/Scripts/python -m pytest -q   # also loads NLI + generator
    .venv/Scripts/python scripts/validate_verifier.py        # verifier vs labeled smoke outputs

## Phase 3 (best-of-N, pairs, human labels)
    .venv/Scripts/python scripts/make_split.py                  # data/split.json (645 train / 120 test)
    .venv/Scripts/python scripts/build_pairs.py --limit 20      # GPU, resumable -> data/candidates.jsonl, data/pairs.jsonl
    .venv/Scripts/python scripts/build_pairs.py --pairs-only    # rebuild pairs from stored candidates (CPU)
    .venv/Scripts/python scripts/eval_bestofn.py                # greedy vs best-of-8 on set-2 reports (label, then --score)
    .venv/Scripts/python scripts/eval_verifier.py               # verifier AUC on all labeled sets

Human labeling: send each teammate `results/human_labeling/GUIDELINES.md` and their sheet from
`results/human_labeling/sheets/`. Completed CSVs go in `results/human_labeling/filled/`, then run
`scripts/score_human_labels.py`. Keep `claude_key.csv` private until everyone has finished.

## Demo
    .venv/Scripts/python scripts/eval_bestofn.py --reports heldout   # GPU, resumable: plain LLM vs best-of-N on 40 held-out reports
    .venv/Scripts/python scripts/build_demo.py                       # picks examples -> demo/examples.json
    .venv/Scripts/python demo/server.py                              # then open http://localhost:8000

The page explains medical terms from `data/glossary.csv` (fixed, human-reviewable, never AI-written);
`scripts/glossary_coverage.py` shows which frequent terms are still missing, and
`scripts/make_glossary_review.py` splits the glossary across the team for review. Glosses are display-only:
all scores and flags are computed on the model's own text.

## 3D body map (demo)
The page places each report sentence on a real-anatomy 3D body (BodyParts3D, CC BY 4.0; credit shown on the page).
One-time setup, all offline afterwards:

    .venv/Scripts/python scripts/fetch_vendor.py      # pinned three.js 0.160.0 + GSAP 3.12.5 -> demo/vendor/
    # download into data/raw/anatomy/ from https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/ :
    #   partof_BP3D_4.0_obj_99.zip (62 MB), partof_parts_list_e.txt, partof_element_parts.txt
    .venv/Scripts/python scripts/build_anatomy.py     # -> demo/assets/anatomy.glb (43 MB), anatomy.json, ATTRIBUTION.txt

If `demo/assets/anatomy.glb` is missing or WebGL is unavailable the page falls back to the flat figure.
The BodyParts3D lungs are airway trees only, so each lobe also gets a translucent shell (convex hull, smoothed).

## More inputs
    .venv/Scripts/python scripts/make_sample_inputs.py   # -> results/review/sample_inputs_more.md (34 demo inputs, held-out test split + SYNTHETIC, grouped by what they exercise)

## Final evaluation run (120 reports, caches every candidate)
    .venv/Scripts/python scripts/eval_bestofn.py --reports final             # GPU, resumable, about 117 s/report (RTX 4060)
    .venv/Scripts/python scripts/eval_bestofn.py --reports final --rescore   # after a verifier change: re-pick from the cache, no generation
`final` = the 40 held-out reports plus 80 more Open-i reports from the train split (never trained on; say so in the write-up).
