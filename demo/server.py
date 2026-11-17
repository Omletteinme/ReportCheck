"""Local demo server (stdlib only): `python demo/server.py`, then open http://localhost:8000.

GET  /              the page
GET  /api/examples  pre-computed examples (demo/examples.json, made by scripts/build_demo.py)
GET  /api/summary   four-system comparison on 120 unseen reports (results/system_comparison.md)
POST /api/extract   raw file bytes + X-Filename header (.txt, .docx, .pdf) -> {"text": str, "chars": int}
POST /api/simplify  {"report": str} -> rule-based plain-language version, instant, no model (src/plainrules.py)
POST /api/run       {"report": str} -> the trained T5 hybrid and the rule-based version, both scored by the verifier
                    T5 writes candidate rewrites sentence by sentence; one is used only if it passes every meaning check,
                    otherwise the rule-based sentence (src/sentencewise.py, src/plainrules.py). A few seconds on the GPU.
The models load on the first live request. One request runs at a time (single GPU).
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
        from src.t5gen import T5Generator
        from src.verify import Verifier

        _models["gen"], _models["verifier"] = T5Generator(), Verifier()
    return _models["gen"], _models["verifier"]


def run(report: str, mode: str = "hybrid") -> dict:
    """The trained T5 hybrid (`selected`) next to the rule-based version (`plain`), each with the verifier's explanation.

    `mode` is accepted for older clients and ignored: there is one live pipeline."""
    from src.glossary import annotate
    from src.plainrules import simplify, simplify_sentence
    from src.sentencewise import simplify as hybrid_simplify
    from src.t5gen import t5_prompt

    gen, verifier = models()
    rules_text = simplify(report)["text"]
    result = hybrid_simplify(gen, verifier.entail_fn, report, fallback=lambda s: simplify_sentence(s)[0], vocab=False, guard=True,
                             n=3, temperature=0.8, max_new_tokens=128, prompt_fn=t5_prompt)
    explained = {"plain": (rules_text, verifier.explain(report, rules_text)),
                 "selected": (result["text"], verifier.explain(report, result["text"]))}
    for _, e in explained.values():
        e["sentences"] = annotate(e["sentences"])
    return {
        "source": report, "mode": "hybrid", "n_candidates": result["rewritten"], "acceptable": True,
        "units": {"model": result["rewritten"], "rules": result["rules"], "total": result["total"]},
        "plain": {"text": explained["plain"][0], "explain": explained["plain"][1]},
        "selected": {"text": explained["selected"][0], "explain": explained["selected"][1]},
    }


def simplify_report(report: str) -> dict:
    """Rule-based plain-language version (src/plainrules.py): instant, no model, no GPU."""
    import textstat

    from src.glossary import gloss_sentences
    from src.plainrules import simplify

    result = simplify(report)
    before = " ".join(s["source"] for s in result["sentences"])
    glossed = gloss_sentences([s["text"] for s in result["sentences"]])   # explanations for terms the rules left in
    return {"text": result["text"], "changed": result["changed"], "total": result["total"],
            "sentences": [{"source": s["source"], "text": s["text"], "changed": s["text"] != s["source"],
                           "parts": [{"t": t, "gloss": g} for t, g in x["parts"]]}
                          for s, x in zip(result["sentences"], glossed)],
            "fk_before": textstat.flesch_kincaid_grade(before), "fk_after": textstat.flesch_kincaid_grade(result["text"])}


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
            path = ROOT / "results" / "system_comparison.md"
            if not path.exists():
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
        if self.path == "/api/simplify":
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                report = str(body.get("report", "")).strip()
            except (ValueError, TypeError):
                return self._json(400, {"error": "invalid request"})
            if not report or len(report) > MAX_REPORT_CHARS:
                return self._json(400, {"error": f"need a report of 1-{MAX_REPORT_CHARS} characters"})
            return self._json(200, simplify_report(report))
        if self.path != "/api/run":
            return self._json(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            report, mode = str(body.get("report", "")).strip(), body.get("mode", "hybrid")
        except (ValueError, TypeError):
            return self._json(400, {"error": "invalid request"})
        if not report or len(report) > MAX_REPORT_CHARS:
            return self._json(400, {"error": f"need a report of 1-{MAX_REPORT_CHARS} characters"})
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
