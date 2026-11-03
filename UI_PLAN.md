# Plan: UI/UX overhaul of the demo page (visual quality, accessibility, motion)

## Context
The user wants the demo's UI and UX improved (visual quality, usability, accessibility, motion) with **no change to
functionality or logic**, using three skill-driven agents: design-director (taste skill), ux-guidelines-auditor
(Web Design Guidelines) and motion-engineer (no GSAP skill exists; user chose **gpt-taste** as its source, plus the
user's motion rules). The three read-only audits are done (below). This plan merges them. The interim review is
tomorrow (Nov 4), so all work happens on a branch and the current `main` demo stays usable.

## Codebase summary
- One static page: `demo/index.html` (716 lines, all CSS inline with tokens as CSS custom properties on `:root`,
  dark mode via `prefers-color-scheme`, inline vanilla JS). `demo/body3d.js` (three.js 0.160 viewer, HTML pin
  buttons, GSAP 3.12.5 global from `/vendor/gsap/gsap.min.js`, no ScrollTrigger). `demo/server.py` (stdlib; untouched).
- No framework, no npm, no Tailwind, no build/lint/typecheck. Node 24 is installed (usable for `node --check`).
- Sections: header (brand, pill nav, prototype chip), 3-column board (intro + report form, 3D map, score stats),
  findings list + verdict, three comparison columns (original / plain / selected), 120-report table.
- Design read (design-director): trust-first clinical research demo; dials VARIANCE 3, MOTION 3, DENSITY 5. Taste
  skill section 13 marks dense product UI out of scope, so only its type/color/spacing/consistency/AI-tell rules apply.

## Conflict rules applied
Accessibility beats taste, taste beats motion. Specific resolutions:
- Flag reasons: visible short reason under each flagged sentence (taste) **and** an sr-only reason + focusable mark
  (a11y). Key text becomes "hover or focus for why".
- Marker colours: taste's neutral "normal" marker is accepted only with a glyph contrast >= 4.5:1 (verify each).
- Hover colour changes stay instant (transform/opacity-only rule); only press feedback animates.
- Copy renames (taste #11) are display text only; anchor ids, API fields and JS keys stay unchanged.

## Setup steps (after approval)
1. `git switch -c ui-polish`.
2. Create `.claude/agents/design-director.md`, `ux-guidelines-auditor.md`, `motion-engineer.md`: each system prompt
   says "read your SKILL.md first and treat it as the source of truth" (paths: `~/.agents/skills/design-taste-frontend`,
   the web-design-guidelines plugin skill path (fetch command.md), `~/.agents/skills/gpt-taste` + the user's motion
   rules), scope = `demo/index.html` and `demo/body3d.js`, no functionality changes, no new libraries/CDNs.
3. Write `UI_PLAN.md` at the repo root with the merged plan below (the audit findings with file:line).
Implementation runs these agents one at a time (if new agent types are not loadable mid-session, run a general-purpose
agent with the same prompt file contents). Each phase ends with a small commit (no push unless asked).

## Phase A: tokens and foundation (design-director)
- Replace the token block with the proposed system: one accent `--accent` (#2453c4 light / #8fb0ff dark) used for
  CTA, active pills/segments and focus; yellow and orange reserved for status only; `--line-strong` for input and
  outline borders; type scale `--fs-xs..--fs-display`; 4px spacing scale `--sp-1..7`; radii rule (pills for
  interactive, 20 cards, 12 nested, 4 data marks); tinted shadow tokens; `color-scheme: light dark`, theme-color metas.
- Font stack: drop the unloaded Inter, start with "Segoe UI Variable Text", system-ui; weights 400/500/600 only;
  `font-variant-numeric: tabular-nums` on scores, timer, table.
- Remove the frame halo and raw shadows; replace hard-coded whites with tokens.
- Hedge levels: keep text in `--ink`, show level by amber underline style (dotted possible, dashed likely, solid
  unlikely-colour) instead of purple text.

## Phase B: layout and components (design-director)
- h1 to one line at `--fs-display` (no `<br>` split); verdict moves to the top of the stats column at `--fs-md`/600.
- Selected-draft column gets a 2px accent border; consistent labels: "Original report", "Plain draft",
  "Checked draft", "the checker"; nav pill "Held-out" -> "Results"; tab title "Report Check".
- Remove repeated "Prototype" chip + dot (keep the one honest note); remove the meaningless stat water-drop icon.
- Spacing to the 4px scale; reduce frame padding below 1000px; fix 320px overflow (`minmax(min(280px,100%),1fr)`).
- Copy fixes (taste #14) and the ellipsis character.

## Phase C: UX and accessibility (ux-guidelines-auditor), in severity order
- Critical: `.body3d-canvas` `touch-action: pan-y pinch-zoom`; figure height `clamp()` + short-screen rule.
- Critical: flag reasons available to keyboard/touch/screen readers (see conflict rules).
- High: marker glyph contrast (dark mode glyph `--on-ink`; light `--mk-finding #c2410c`); `.figure.is3d
  overflow: clip` and hide off-canvas pins from tab order; live region announces only start/done/error (ticking
  seconds `aria-hidden`); explicit 409/non-JSON error text in `--bad`; try/catch + messages for `/api/examples` and
  `/api/summary`; `--bar-strong` for supported-sentence bars; 3:1 borders for textarea and ghost button.
- Medium: `--lvl-unlikely #5d6b80`, `.tag.good` colour; amber border for uncertain caption; pin hit area 24px
  (44px on coarse pointers, dot size unchanged); busy state with `aria-busy` and focus kept (no focus loss on
  disabled button); empty-report error with `aria-invalid` + focus; reserve space for the Chest/Whole body switch;
  pin tab order top-to-bottom; wheel zoom only with Ctrl (or when pointer pressed) so the page scrolls.
- Low: hint text only in 3D mode with touch wording; keyboard-reachable table scroll region; `spellcheck=false`
  on the report; `role="group"` where aria-label sits on divs; hidden h2 for stats; pill strip focus-ring padding;
  hover states for `.cta`/`.seg-b`; title-only info made visible or sr-available.

## Phase D: motion (motion-engineer), last
- P1: result swap entrance (opacity + y 8px, 0.3 s, column stagger 0.06 s) only when the report changes, via one
  `gsap.context` reverted before each render; score bars via transform (translateX fill) 0.6 s; running-check state:
  old results dim to 0.5 + `aria-busy`, a one-shot 2px progress bar (scaleX to 0.9 over expected time, completes on
  done, killed in `finally`); CSS press feedback `scale(.97)` under `prefers-reduced-motion: no-preference`.
- P2: gentler pin pop (`back.out(1.2)`, no replay when markers unchanged); reduced-motion guard for the skin fade and
  `enableDamping`; shorter reveal swing (0.5 rad, 1.4 s); caption fade on selection.
- P3: support-chart bar grow, CTA arrow nudge on hover; remove the stale `setBusy` comment in body3d.js.
- Everything collapses to instant under reduced motion; no loops; transform/opacity only.

## Verification
- `node --check demo/body3d.js`; extract the inline module script and `node --check` it; `pytest -q` (server tests).
- Start `demo/server.py`, open http://localhost:8000 in the browser pane at 375, 768 and 1440 px, light and dark:
  screenshots, no console errors, run an example, Quick check path (busy, error 409 by double click, success),
  keyboard-only pass (tab through pins, switches, flagged words), reduced-motion emulation.
- ux-guidelines-auditor re-audits the final files; report what changed, before/after screenshots, what is left.
- Merge `ui-polish` into `main` only after the user sees it (the review is tomorrow).

## Out of scope
Server, verifier, data, evaluation results, the 3D model asset, new libraries or web fonts from a CDN.
