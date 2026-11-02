"""Build demo/assets/anatomy.glb and anatomy.json from BodyParts3D (CC BY 4.0), run once.

Input  (download first, see README), in data/raw/anatomy/:
       partof_BP3D_4.0_obj_99.zip, partof_parts_list_e.txt,
       partof_element_parts.txt (FMA concept id -> FJ element meshes; each organ is a union of elements)
Output: demo/assets/anatomy.glb   named nodes (skin, lung_*, heart, ribs, ...), metres, x=left y=up z=anterior
        demo/assets/anatomy.json  one anchor point + highlight nodes per page region id, camera framing hints
        demo/assets/ATTRIBUTION.txt
"""
import collections
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.anatomy import GROUPS, HULL, LEFT_LUNG, RIGHT_LUNG, keep_near, orientation, region_anchors, select_parts  # noqa: E402

RAW = ROOT / "data" / "raw" / "anatomy"
OUT = ROOT / "demo" / "assets"
CREDIT = "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International"
LICENSE_URL = "https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html"
OPTIONAL = {"skin"}


def read_tsv(name: str) -> list[list[str]]:
    lines = (RAW / name).read_text(encoding="utf-8").splitlines()[1:]
    return [line.split("\t") for line in lines]


def read_part_names() -> dict[str, str]:
    """part name -> FMA concept id"""
    return {r[2]: r[0] for r in read_tsv("partof_parts_list_e.txt")}


def read_elements() -> dict[str, list[str]]:
    """FMA concept id -> element mesh ids (FJ####)"""
    elements = collections.defaultdict(list)
    for concept, _name, element in read_tsv("partof_element_parts.txt"):
        elements[concept].append(element)
    return elements


def load_group(zf: zipfile.ZipFile, members: dict[str, str], elements: dict[str, list[str]],
               parts: list[tuple[str, str]]) -> trimesh.Trimesh:
    meshes = []
    for name, concept in parts:
        files = elements.get(concept, [])
        found = [members[f] for f in files if f in members]
        if not found:
            raise SystemExit(f"{name} ({concept}): none of its {len(files)} element meshes are in the archive")
        meshes += [trimesh.load(io.BytesIO(zf.read(m)), file_type="obj", force="mesh", process=True) for m in found]
    return trimesh.util.concatenate(meshes)


def main():
    found, missing = select_parts(read_part_names())
    hard_missing = [n for n in missing if not any(n in GROUPS[g] and g in OPTIONAL for g in GROUPS)]
    if hard_missing:
        raise SystemExit(f"parts not in the parts list: {hard_missing}")
    for g in OPTIONAL - set(found):
        print(f"note: no '{g}' part found; the page will draw a procedural silhouette")

    with zipfile.ZipFile(RAW / "partof_BP3D_4.0_obj_99.zip") as zf:
        members = {Path(n).stem: n for n in zf.namelist() if n.lower().endswith(".obj")}
        print(f"{len(members)} OBJ files in the archive")
        elements = read_elements()
        meshes = {g: load_group(zf, members, elements, parts) for g, parts in found.items()}

    centers = {k: m.bounds.mean(axis=0) for k, m in meshes.items()}
    lump = lambda names: trimesh.util.concatenate([meshes[n] for n in names if n in meshes]).bounds.mean(axis=0)  # noqa: E731
    r = orientation({"brain": centers["brain"], "pelvis": centers["pelvis"], "lung_l": lump(LEFT_LUNG),
                     "lung_r": lump(RIGHT_LUNG), "heart": centers["heart"], "spine": centers["spine"]})
    print("rotation (new = R @ old):\n", r)

    # rotate, mm -> metres, and put the middle of the lungs at the origin
    for m in meshes.values():
        m.vertices = (r @ m.vertices.T).T * 0.001
    lungs = trimesh.util.concatenate([meshes[k] for k in RIGHT_LUNG + LEFT_LUNG if k in meshes])
    origin = lungs.bounds.mean(axis=0)
    for m in meshes.values():
        m.vertices = m.vertices - origin
    lo = np.min([m.bounds[0] for m in meshes.values()], axis=0)
    hi = np.max([m.bounds[1] for m in meshes.values()], axis=0)
    print(f"body extent (m): x {hi[0] - lo[0]:.2f}  y {hi[1] - lo[1]:.2f}  z {hi[2] - lo[2]:.2f}")
    if not 1.2 < hi[1] - lo[1] < 2.3:
        raise SystemExit("body height is not 1.2-2.3 m: the archive units are not millimetres?")

    # the BodyParts3D lobe meshes include a few pieces far from the lungs (e.g. 2 pieces 17 cm below the right
    # upper lobe); drop lung pieces whose centroid is more than 16.5 cm from the middle of the lungs
    middle = np.median(np.vstack([meshes[k].vertices for k in RIGHT_LUNG + LEFT_LUNG if k in meshes]), axis=0)
    for k in RIGHT_LUNG + LEFT_LUNG:
        pieces = meshes[k].split(only_watertight=False)
        mask = keep_near(np.array([p.vertices.mean(axis=0) for p in pieces]), middle, 0.165)
        if not mask.all():
            print(f"{k}: dropped {int((~mask).sum())} stray piece(s), {sum(len(p.vertices) for p, m in zip(pieces, mask) if not m)} vertices")
            meshes[k] = trimesh.util.concatenate([p for p, m in zip(pieces, mask) if m])

    anchor_vertices = {k: m.vertices for k, m in meshes.items()}   # tree geometry, before the shells are added
    for k in RIGHT_LUNG + LEFT_LUNG:                                  # translucent shell around each airway tree
        shell = trimesh.Trimesh(vertices=meshes[k].vertices, process=False).convex_hull.subdivide().subdivide()
        trimesh.smoothing.filter_taubin(shell, lamb=0.5, nu=-0.53, iterations=12)   # round off the polyhedron
        meshes[k + HULL] = shell

    scene = trimesh.Scene()
    for name, m in meshes.items():
        m.fix_normals()
        _ = m.vertex_normals  # smooth per-vertex normals are exported with the mesh
        scene.add_geometry(m, node_name=name, geom_name=name)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "anatomy.glb").write_bytes(scene.export(file_type="glb"))

    anchors = region_anchors(anchor_vertices)
    lung_b = lungs.bounds - origin
    lung_h, lung_w = float(lung_b[1][1] - lung_b[0][1]), float(lung_b[1][0] - lung_b[0][0])
    meta = {
        "regions": anchors,
        "overview": {"target": [0.0, 0.0, 0.0], "height": round(lung_h * 3.6, 3), "width": round(max(lung_w * 1.7, 0.5), 3)},
        # whole figure, head to feet, with the arms hanging at the sides
        "full": {"target": [0.0, round(float((lo[1] + hi[1]) / 2), 3), 0.0], "height": round(float(hi[1] - lo[1]) * 1.06, 3),
                 "width": round(float(hi[0] - lo[0]) * 1.1, 3)},
        "bounds": {"min": [round(float(x), 3) for x in lo], "max": [round(float(x), 3) for x in hi]},
        "credit": CREDIT, "license": LICENSE_URL,
    }
    (OUT / "anatomy.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    (OUT / "ATTRIBUTION.txt").write_text(
        f"{CREDIT}\n{LICENSE_URL}\nProcessed (rotated, scaled, merged) by scripts/build_anatomy.py.\n", encoding="utf-8")
    size = (OUT / "anatomy.glb").stat().st_size / 1e6
    print(f"anatomy.glb {size:.1f} MB; nodes: {', '.join(f'{k}={len(m.vertices)}v' for k, m in meshes.items())}")
    for rid, a in anchors.items():
        print(f"  {rid:14} {a['anchor']}")


if __name__ == "__main__":
    main()
