"""Download pinned three.js and GSAP into demo/vendor/ so the demo works offline (run once).

Folder layout is kept (three/build, three/examples/jsm/...) because the addon modules import each other by
relative path; the page's import map points "three" and "three/addons/" at these files.
"""
import urllib.request
from pathlib import Path

VENDOR = Path(__file__).resolve().parent.parent / "demo" / "vendor"
THREE = "0.160.0"
GSAP = "3.12.5"
CDN = "https://cdn.jsdelivr.net/npm"
FILES = {
    "three/build/three.module.min.js": f"{CDN}/three@{THREE}/build/three.module.min.js",
    "three/examples/jsm/controls/OrbitControls.js": f"{CDN}/three@{THREE}/examples/jsm/controls/OrbitControls.js",
    "three/examples/jsm/loaders/GLTFLoader.js": f"{CDN}/three@{THREE}/examples/jsm/loaders/GLTFLoader.js",
    "three/examples/jsm/utils/BufferGeometryUtils.js": f"{CDN}/three@{THREE}/examples/jsm/utils/BufferGeometryUtils.js",
    "gsap/gsap.min.js": f"{CDN}/gsap@{GSAP}/dist/gsap.min.js",
}


def main():
    for rel, url in FILES.items():
        path = VENDOR / rel
        if path.exists() and path.stat().st_size > 1000:
            print(f"have {rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            path.write_bytes(r.read())
        print(f"got  {rel} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
