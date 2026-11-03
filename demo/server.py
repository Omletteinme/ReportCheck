"""Local demo server (stdlib only): `python demo/server.py`, then open http://localhost:8000.

GET  /              the page
GET  /api/examples  pre-computed examples (demo/examples.json, made by scripts/build_demo.py)
GET  /api/summary   comparison table on 120 unseen reports (results/final_summary.md)
POST /api/extract   raw file bytes + X-Filename header (.txt, .docx, .pdf) -> {"text": str, "chars": int}
POST /api/run       {"report": str, "mode": "quick" | "best"} -> live drafts scored by the verifier
                    quick = baseline draft + structured draft, best of the two (~30 s)
                    best  = best of 10 sampled drafts plus the baseline draft (~2-3 min)
The model loads on the first live request. One request runs at a time (single GPU).
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
DEMO = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from demo.extract import MAX_BYTES, ExtractError, extract_text  # noqa: E402

PORT = 8000
STATIC_ROOTS = {"vendor": DEMO / "vendor", "assets": DEMO / "assets"}  # /vendor/... and /assets/...
STATIC_FILES = {"/body3d.js": DEMO / "body3d.js"}
MIME = {".js": "text/javascript; charset=utf-8", ".glb": "model/gltf-binary",
        ".json": "application/json; charset=utf-8", ".txt": "text/plain; charset=utf-8"}
MAX_REPORT_CHARS = 3000
_lock = threading.Lock()
_models: dict = {}


def static_file(url_path: str, roots=None, files=None) -> tuple[Path, str] | None:
    """Resolve a static URL to (file, mime type), or None when unknown, disallowed or outside its folder."""
    roots, files = roots or STATIC_ROOTS, files or STATIC_FILES
    path = unquote(url_path.split("?", 1)[0])
    if path in files:
        candidate = files[path]
    else:
        folder, _, rest = path.lstrip("/").partition("/")
        if folder not in roots or not rest:
            return None
        base = roots[folder].resolve()
        candidate = (base / rest).resolve()
        if base not in candidate.parents:  # blocks ../ traversal and absolute-path tricks
            return None
    mime = MIME.get(candidate.suffix.lower())
    return (candidate, mime) if mime and candidate.is_file() else None


def models():
    if not _models:
        from src.generate import Generator
        from src.verify import Verifier

        _models["gen"], _models["verifier"] = Generator(), Verifier()
    return _models["gen"], _models["verifier"]


def run(report: str, mode: str) -> dict:
    from src.bestofn import acceptable, best_of_n, choose, rank
    from src.generate import build_prompt
    from src.glossary import annotate

    gen, verifier = models()
    plain = gen.generate(build_prompt(report, "baseline"), max_new_tokens=400)[0]
    if mode == "best":
        ranked = best_of_n(gen, verifier, report, 8, extra=(plain,), max_new_tokens=400)
    else:
        drafts = [plain, gen.generate(build_prompt(report, "structured"), max_new_tokens=400)[0]]
        ranked = rank(verifier, report, [d for d in dict.fromkeys(drafts) if d])
    best = choose(ranked)
    selected = best.text if best else plain
    explained = {"plain": (plain, verifier.explain(report, plain)), "selected": (selected, verifier.explain(report, selected))}
    for _, e in explained.values():
        e["sentences"] = annotate(e["sentences"])
    return {
        "source": report, "mode": mode, "n_candidates": len(ranked),
        "acceptable": bool(best and acceptable(best.score)),
        "plain": {"text": plain, "explain": explained["plain"][1]},
        "selected": {"text": selected, "explain": explained["selected"][1]},
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, ctype: str):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, obj):
        self._send(status, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (DEMO / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/examples":
            path = DEMO / "examples.json"
            self._json(200, json.loads(path.read_text(encoding="utf-8")) if path.exists() else [])
        elif self.path == "/api/summary":
            path = ROOT / "results" / "final_summary.md"
            self._json(200, {"markdown": path.read_text(encoding="utf-8") if path.exists() else ""})
        elif found := static_file(self.path):
            file, mime = found
            self.send_response(200)
            self.send_header("Content-Type", mime)
            body = file.read_bytes()
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache" if file.name == "body3d.js" else "public, max-age=3600")
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json(404, {"error": "not found"})

    def _extract(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > MAX_BYTES:
            return self._json(413, {"error": "That file is larger than 5 MB."})
        try:
            text = extract_text(unquote(self.headers.get("X-Filename", "")), self.rfile.read(length))
        except ExtractError as e:
            return self._json(400, {"error": str(e)})
        self._json(200, {"text": text, "chars": len(text)})

    def do_POST(self):
        if self.path == "/api/extract":
            return self._extract()
        if self.path != "/api/run":
            return self._json(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            report, mode = str(body.get("report", "")).strip(), body.get("mode", "quick")
        except (ValueError, TypeError):
            return self._json(400, {"error": "invalid request"})
        if not report or len(report) > MAX_REPORT_CHARS or mode not in ("quick", "best"):
            return self._json(400, {"error": f"need a report of 1-{MAX_REPORT_CHARS} characters and mode quick|best"})
        if not _lock.acquire(blocking=False):
            return self._json(409, {"error": "another request is still running, try again in a minute"})
        try:
            self._json(200, run(report, mode))
        except Exception as e:  # report the failure to the page instead of dropping the connection
            self._json(500, {"error": f"{type(e).__name__}: {e}"})
        finally:
            _lock.release()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Demo running at http://localhost:{PORT} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
