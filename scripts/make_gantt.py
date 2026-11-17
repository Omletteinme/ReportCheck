"""Project Gantt chart -> results/review/project_gantt.png and .svg.

    .venv/Scripts/python scripts/make_gantt.py

Edit TASKS (and FINAL, TODAY) below and rerun. Dates of finished work are approximate (taken from the commit history and result
files); dates of planned work are a proposal; the final deadline is an assumption (the course says "first week of December").
"""
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "review"
INK, MUTED, LINE, ACCENT, DONE, FINAL_COLOR = "#14171f", "#596173", "#e1e5ec", "#2453c4", "#8a93a3", "#c0392b"
TODAY, FINAL = date(2026, 11, 16), date(2026, 12, 3)

# (group, task, start, end, status) with status "done" or "planned"
TASKS = [
    ("Build", "Data, split and verifier", date(2026, 10, 26), date(2026, 11, 2), "done"),
    ("Build", "Best-of-N evaluation and blind labeling", date(2026, 11, 1), date(2026, 11, 3), "done"),
    ("Build", "Demo: 3D body map, upload, findings explorer", date(2026, 11, 2), date(2026, 11, 4), "done"),
    ("Build", "Rule-based simplifier and word table", date(2026, 11, 5), date(2026, 11, 8), "done"),
    ("Build", "T5 fine-tuning and checks (hybrid)", date(2026, 11, 8), date(2026, 11, 10), "done"),
    ("Build", "Blind labeling of the new systems", date(2026, 11, 10), date(2026, 11, 11), "done"),
    ("Build", "Demo switched to the T5 hybrid", date(2026, 11, 11), date(2026, 11, 12), "done"),
    ("Evidence", "Teammate review of the rule table", date(2026, 11, 17), date(2026, 11, 21), "planned"),
    ("Evidence", "Hand-check 40 outputs (human labels)", date(2026, 11, 18), date(2026, 11, 23), "planned"),
    ("Evidence", "Random-pick ablation (best-of-N)", date(2026, 11, 18), date(2026, 11, 19), "planned"),
    ("Write-up", "Paper and report: four-system table, limits", date(2026, 11, 17), date(2026, 11, 27), "planned"),
    ("Write-up", "Refresh figures and screenshots", date(2026, 11, 22), date(2026, 11, 25), "planned"),
    ("Write-up", "Slides and demo rehearsal", date(2026, 11, 24), date(2026, 12, 1), "planned"),
    ("Final", "Final check, commit, push and submit", date(2026, 12, 1), date(2026, 12, 3), "planned"),
]

plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10.5, "text.color": INK, "axes.edgecolor": LINE})


def main():
    fig, ax = plt.subplots(figsize=(12.5, 6.4))
    rows = list(reversed(TASKS))
    for i, (group, task, start, end, status) in enumerate(rows):
        color = DONE if status == "done" else ACCENT
        ax.barh(i, (end - start).days + 1, left=mdates.date2num(start), height=0.56, color=color, zorder=3)
        ax.text(mdates.date2num(end) + 1.3, i, f"{start:%b %d}-{end:%b %d}", va="center", fontsize=8.5, color=MUTED, zorder=5,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2, "alpha": 0.85})
    ax.set_yticks(range(len(rows)), [f"{t[1]}" for t in rows])
    # group labels on the left margin
    seen = {}
    for i, (group, *_rest) in enumerate(rows):
        seen.setdefault(group, []).append(i)
    for group, idx in seen.items():
        ax.text(-0.36, (min(idx) + max(idx)) / 2, group, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=11, fontweight="bold", color=MUTED)
        ax.axhline(max(idx) + 0.5, color=LINE, lw=1, zorder=1)
    ax.axvline(mdates.date2num(TODAY), color=INK, lw=1.3, ls="--", zorder=4)
    ax.text(mdates.date2num(TODAY) - 0.4, len(rows) - 0.35, f"Today, {TODAY:%b %d}", fontsize=9, fontweight="bold", va="bottom", ha="right")
    ax.axvline(mdates.date2num(FINAL), color=FINAL_COLOR, lw=1.6, zorder=4)
    ax.text(mdates.date2num(FINAL) - 0.4, len(rows) - 0.35, f"Final deadline (assumed), {FINAL:%b %d}", fontsize=9, fontweight="bold",
            color=FINAL_COLOR, va="bottom", ha="right")
    ax.set_xlim(mdates.date2num(date(2026, 10, 24)), mdates.date2num(date(2026, 12, 8)))
    ax.set_ylim(-0.7, len(rows) + 0.35)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.grid(axis="x", color=LINE, lw=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_axisbelow(True)
    ax.set_title("Radiology report simplification: project timeline", loc="left", fontsize=14, fontweight="bold", pad=22)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=DONE), plt.Rectangle((0, 0), 1, 1, color=ACCENT)],
              labels=["Done (dates approximate)", "Planned (proposed dates)"], loc="center", bbox_to_anchor=(0.68, 0.72), frameon=False, fontsize=9.5)
    fig.text(0.01, 0.01, "Final deadline is an assumption (the course says the first week of December). Edit TASKS in scripts/make_gantt.py to change dates.",
             fontsize=8.5, color=MUTED)
    fig.subplots_adjust(left=0.36, right=0.97, top=0.9, bottom=0.1)
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"project_gantt.{ext}", dpi=200 if ext == "png" else None)
    print("saved", OUT / "project_gantt.png")


if __name__ == "__main__":
    main()
