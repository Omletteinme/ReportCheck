"""Capture the demo's important screens into figures/demo/ (PNG, 2x resolution).

    .venv/Scripts/python scripts/capture_screenshots.py [--live]

Needs `pip install playwright` (see requirements-figures.txt); it drives the installed Microsoft Edge, so no browser
download. Starts demo/server.py if nothing answers on :8000 and stops it afterwards. Reduced motion is emulated so the
shots are deterministic (no title scramble, no camera swing). Examples come from demo/examples.json (no GPU needed);
--live also runs one real Quick check (about 30 s, uses the GPU) for the progress and result shots.
"""
import argparse
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "figures" / "demo"
URL = "http://localhost:8000"
VIEW = {"width": 1440, "height": 900}
EXAMPLE = {"biggest_gain": 0, "number": 1, "hedge_restored": 2, "left_right": 3}   # chip order on the page


def server_up() -> bool:
    try:
        urllib.request.urlopen(URL + "/api/summary", timeout=2)
        return True
    except OSError:
        return False


def start_server():
    if server_up():
        return None
    proc = subprocess.Popen([sys.executable, str(ROOT / "demo" / "server.py")], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if server_up():
            return proc
        time.sleep(0.5)
    proc.kill()
    raise SystemExit("the demo server did not start")


def launch(p, headless=True):
    args = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] if headless else []
    return p.chromium.launch(channel="msedge", headless=headless, args=args)


def open_page(browser, viewport=VIEW, **ctx):
    context = browser.new_context(viewport=viewport, device_scale_factor=2, reduced_motion="reduce", color_scheme="light", **ctx)
    page = context.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(URL)
    page.wait_for_selector("#chips .chip", timeout=15000)
    return page, errors


def webgl_ready(page, timeout=20000) -> bool:
    try:
        page.wait_for_function("document.getElementById('figure').classList.contains('is3d')", timeout=timeout)
        return True
    except Exception:
        return False


def pick(page, key):
    page.locator("#chips .chip").nth(EXAMPLE[key]).click()
    page.wait_for_selector(".co", timeout=15000)       # callout cards appear once the pins have a position
    page.wait_for_timeout(1500)                        # glide, highlight and leader lines settle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="also run one real Quick check (GPU, about 30 s)")
    live = ap.parse_args().live
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    server = start_server()
    made: list[str] = []

    def shot(page, name, target=None, full=False):
        path = OUT / f"{name}.png"
        if target is None:
            page.screenshot(path=str(path), full_page=full)
        else:
            # clip instead of element.screenshot(): the WebGL map never counts as "stable"
            el = page.locator(target).first
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            box = el.evaluate("e => { const r = e.getBoundingClientRect(); return {x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height}; }")
            page.screenshot(path=str(path), clip=box, full_page=True)
        made.append(name)
        print("saved", path.name, flush=True)

    try:
        with sync_playwright() as p:
            browser = launch(p)
            page, errors = open_page(browser)
            if not webgl_ready(page):
                print("WebGL not available headless, retrying with a visible window", flush=True)
                browser.close()
                browser = launch(p, headless=False)
                page, errors = open_page(browser)
                if not webgl_ready(page):
                    raise SystemExit("the 3D figure never loaded")
            page.wait_for_timeout(1500)

            shot(page, "01-overview-empty")
            pick(page, "biggest_gain")
            shot(page, "02-full-ui-example")
            shot(page, "02b-full-page", full=True)
            shot(page, "03-input-panel", ".controls")

            # upload: a .txt file is read by the server and filled into the box
            src = page.evaluate("() => document.getElementById('report').value")
            with tempfile.TemporaryDirectory() as tmp:
                f = Path(tmp) / "sample-report.txt"
                f.write_text(src, encoding="utf-8")
                page.set_input_files("#fileIn", str(f))
                page.wait_for_function("document.getElementById('status').textContent.startsWith('Loaded')", timeout=10000)
            shot(page, "04-upload-loaded", ".controls")

            pick(page, "left_right")
            shot(page, "05-body-map-callouts", "#stage")
            page.locator(".co").first.click()
            page.wait_for_timeout(1500)
            shot(page, "06-body-map-selected", ".map")
            page.locator(".co").first.click()               # deselect
            page.locator("#viewBody").click()
            page.wait_for_timeout(1500)
            shot(page, "07-body-map-whole-body", "#stage")
            page.locator("#viewChest").click()
            page.wait_for_timeout(800)
            shot(page, "08-map-patient-version", ".map")
            page.locator("#modeOriginal").click()
            page.wait_for_timeout(1200)
            shot(page, "09-map-original-report", ".map")
            page.locator("#modePatient").click()
            page.wait_for_timeout(800)

            for tab, name in ((2, "10-output-checked-draft"), (1, "11-output-plain-draft"), (0, "12-output-original")):
                page.locator(f"#outTab{tab}").click()
                page.wait_for_timeout(500)
                shot(page, name, "#result")

            # a flagged word with its reason bubble (plain drafts carry the flags)
            for key in ("left_right", "number", "biggest_gain"):
                pick(page, key)
                page.locator("#outTab1").click()
                marks = page.locator("#outpanel mark.flag")
                if marks.count():
                    marks.first.scroll_into_view_if_needed()
                    marks.first.hover()
                    page.wait_for_timeout(400)
                    shot(page, f"13-flag-tooltip-{key}", "#result")
                    page.mouse.move(5, 5)

            pick(page, "hedge_restored")
            page.locator("#outTab1").click(); page.wait_for_timeout(400)
            shot(page, "14a-hedge-plain-draft", "#result")
            page.locator("#outTab2").click(); page.wait_for_timeout(400)
            shot(page, "14b-hedge-checked-draft", "#result")

            pick(page, "biggest_gain")
            shot(page, "15-findings-explorer", "#finder")
            page.locator('.fchip[data-f="uncertain"]').click()
            page.wait_for_timeout(600)
            shot(page, "16-findings-filter-hedged", "#finder")

            heldout = page.locator("#heldout")
            if heldout.is_visible():
                shot(page, "17-results-table-120", "#heldout")

            mobile, _ = open_page(browser, viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
            webgl_ready(mobile)
            mobile.locator("#chips .chip").nth(EXAMPLE["biggest_gain"]).click()
            mobile.wait_for_timeout(1800)
            shot(mobile, "18a-mobile-top")
            shot(mobile, "18b-mobile-full-page", full=True)
            shot(mobile, "18c-mobile-output", "#result")

            if live:
                page.reload()
                page.wait_for_selector("#chips .chip")
                webgl_ready(page)
                page.fill("#report", src)
                page.locator("#quick").click()
                page.wait_for_timeout(4000)
                shot(page, "19-live-run-progress", ".controls")
                page.wait_for_function("document.getElementById('quick').getAttribute('aria-disabled') !== 'true'", timeout=240000)
                page.wait_for_timeout(2500)
                shot(page, "20-live-run-result")
                shot(page, "21-live-run-output", "#result")
            if errors:
                print("console errors:", errors[:5])
            browser.close()
    finally:
        if server:
            server.terminate()
    print(f"{len(made)} screenshots in {OUT}")


if __name__ == "__main__":
    main()
