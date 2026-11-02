"""Anatomy helpers for the 3D body map (numpy only; mesh IO lives in scripts/build_anatomy.py).

BodyParts3D parts are picked by exact name, rotated into a fixed frame (x = patient's left, y = up,
z = anterior, metres), and turned into one anchor point per region id used by the demo page.
"""
import numpy as np

ORDINALS = "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth".split()

# glb node name -> exact BodyParts3D part names ("partof" list)
GROUPS: dict[str, list[str]] = {
    "skin": ["skin"],
    "lung_r_upper": ["upper lobe of right lung"],
    "lung_r_mid": ["middle lobe of lung"],
    "lung_r_lower": ["lower lobe of right lung"],
    "lung_l_upper": ["upper lobe of left lung"],
    "lung_l_lower": ["lower lobe of left lung"],
    "heart": ["heart"],
    "airway": ["trachea"],
    "aorta": ["aorta"],
    "diaphragm": ["diaphragm"],
    "ribs": [f"{side} {o} rib" for side in ("left", "right") for o in ORDINALS],
    "sternum": ["sternum"],
    "clavicles": ["left clavicle", "right clavicle"],
    "spine": ["vertebral column"],
    "liver": ["liver"],
    "stomach": ["stomach"],
    "brain": ["brain"],
    "skull": ["skull"],
    "pelvis": ["bony pelvis"],
    # limbs: shown for a complete body, no region of the page points at them
    "arm_bones": [f"{side} {b}" for side in ("left", "right") for b in ("scapula", "humerus", "radius", "ulna")]
    + [f"skeleton of {side} hand proper" for side in ("left", "right")],
    "leg_bones": [f"{side} {b}" for side in ("left", "right") for b in
                  ("femur", "patella", "tibia", "fibula", "talus", "calcaneus", "cuboid bone", "medial cuneiform bone",
                   "intermediate cuneiform bone", "lateral cuneiform bone", "first metatarsal bone",
                   "second metatarsal bone", "third metatarsal bone", "fourth metatarsal bone", "fifth metatarsal bone")]
    + [f"navicular bone of {side} foot" for side in ("left", "right")],
}
RIGHT_LUNG = ["lung_r_upper", "lung_r_mid", "lung_r_lower"]
LEFT_LUNG = ["lung_l_upper", "lung_l_lower"]
# BodyParts3D lungs are airway trees only, so each lobe also gets a translucent shell (convex hull) named <lobe>_hull
HULL = "_hull"


def with_hulls(nodes: list[str]) -> list[str]:
    return [x for n in nodes for x in ((n, n + HULL) if n in RIGHT_LUNG + LEFT_LUNG else (n,))]


# page region id -> glb nodes to highlight
REGION_NODES: dict[str, list[str]] = {
    "head": ["brain", "skull"],
    "neck": ["airway"],
    "mediastinum": ["aorta", "airway"],
    "heart": ["heart"],
    "lung-r-upper": with_hulls(["lung_r_upper"]), "lung-r-mid": with_hulls(["lung_r_mid"]),
    "lung-r-lower": with_hulls(["lung_r_lower"]),
    "lung-l-upper": with_hulls(["lung_l_upper"]), "lung-l-mid": with_hulls(["lung_l_upper", "lung_l_lower"]),
    "lung-l-lower": with_hulls(["lung_l_lower"]),
    "pleura-r": with_hulls(RIGHT_LUNG), "pleura-l": with_hulls(LEFT_LUNG),
    "ribs": ["ribs", "sternum", "clavicles"],
    "spine": ["spine"],
    "diaphragm": ["diaphragm"],
    "abdomen": ["liver", "stomach"],
    "pelvis": ["pelvis"],
}


def select_parts(name_to_id: dict[str, str], groups: dict[str, list[str]] = GROUPS):
    """({group: [(part name, id)]}, [missing part names]) by exact, case-insensitive name."""
    lookup = {n.lower(): (n, i) for n, i in name_to_id.items()}
    found: dict[str, list[tuple[str, str]]] = {}
    missing: list[str] = []
    for group, names in groups.items():
        for name in names:
            hit = lookup.get(name.lower())
            if hit:
                found.setdefault(group, []).append(hit)
            else:
                missing.append(name)
    return found, missing


def _signed_axis(vec: np.ndarray, exclude: tuple[int, ...] = ()) -> tuple[int, int]:
    v = np.abs(np.asarray(vec, dtype=float)).copy()
    v[list(exclude)] = -1
    axis = int(np.argmax(v))
    return axis, int(np.sign(vec[axis])) or 1


def orientation(c: dict[str, np.ndarray]) -> np.ndarray:
    """Rotation R (new = R @ old) taking a dataset frame to x = left, y = up, z = anterior.

    Landmarks: up = brain above pelvis; left = left lung beyond right lung; anterior = heart in front of spine.
    Raises if the result would be a mirror image (left/right labels inconsistent with up/anterior).
    """
    up, sup = _signed_axis(c["brain"] - c["pelvis"])
    left, sleft = _signed_axis(c["lung_l"] - c["lung_r"], (up,))
    ant, sant = _signed_axis(c["heart"] - c["spine"], (up, left))
    r = np.zeros((3, 3))
    r[0, left], r[1, up], r[2, ant] = sleft, sup, sant
    if np.linalg.det(r) < 0:
        raise ValueError("landmarks give a mirrored frame; check left/right part names")
    return r


def _bbox_center(v: np.ndarray) -> np.ndarray:
    """Median of the vertices: robust to a few stray pieces, equal to the box centre for evenly spread points."""
    return np.median(v, axis=0)


def _extreme_mean(v: np.ndarray, axis: int, high: bool, frac: float = 0.08) -> np.ndarray:
    """Mean of the vertices in the outermost `frac` of the range along `axis`."""
    lo, hi = v[:, axis].min(), v[:, axis].max()
    cut = hi - frac * (hi - lo) if high else lo + frac * (hi - lo)
    sel = v[v[:, axis] >= cut] if high else v[v[:, axis] <= cut]
    return sel.mean(axis=0)


def region_anchors(v: dict[str, np.ndarray]) -> dict[str, dict]:
    """{region id: {anchor [x, y, z], nodes [...]}} from oriented vertex arrays keyed by glb node name."""
    lungs_r, lungs_l = np.vstack([v[k] for k in RIGHT_LUNG]), np.vstack([v[k] for k in LEFT_LUNG])
    mid_x = (_bbox_center(lungs_r)[0] + _bbox_center(lungs_l)[0]) / 2
    heart = _bbox_center(v["heart"])
    lung_y0 = min(lungs_r[:, 1].min(), lungs_l[:, 1].min())
    lung_y1 = max(lungs_r[:, 1].max(), lungs_l[:, 1].max())
    spine_chest = v["spine"][(v["spine"][:, 1] >= lung_y0) & (v["spine"][:, 1] <= lung_y1)]
    ribs_r = _extreme_mean(v["ribs"], 0, False, 0.05)
    a = {
        "head": _bbox_center(v["brain"]),
        "neck": _extreme_mean(v["airway"], 1, True, 0.1),
        "mediastinum": np.array([mid_x, heart[1] + 0.03, heart[2]]),
        "heart": heart,
        "lung-r-upper": _bbox_center(v["lung_r_upper"]), "lung-r-mid": _bbox_center(v["lung_r_mid"]),
        "lung-r-lower": _bbox_center(v["lung_r_lower"]),
        "lung-l-upper": _bbox_center(v["lung_l_upper"]), "lung-l-lower": _bbox_center(v["lung_l_lower"]),
        "pleura-r": _extreme_mean(v["lung_r_lower"], 0, False, 0.12),
        "pleura-l": _extreme_mean(v["lung_l_lower"], 0, True, 0.12),
        "ribs": np.array([ribs_r[0], (lung_y0 + lung_y1) / 2, ribs_r[2]]),
        "spine": spine_chest.mean(axis=0) if len(spine_chest) else _bbox_center(v["spine"]),
        "diaphragm": _extreme_mean(v["diaphragm"], 1, True, 0.1),
        "abdomen": (_bbox_center(v["liver"]) + _bbox_center(v["stomach"])) / 2,
        "pelvis": _bbox_center(v["pelvis"]),
    }
    a["lung-l-mid"] = (a["lung-l-upper"] + a["lung-l-lower"]) / 2
    return {rid: {"anchor": [round(float(x), 4) for x in a[rid]], "nodes": REGION_NODES[rid]} for rid in REGION_NODES}


def keep_near(centroids: np.ndarray, center: np.ndarray, radius: float) -> np.ndarray:
    """Boolean mask of mesh pieces whose centroid lies within `radius` of `center` (drops stray pieces)."""
    return np.linalg.norm(np.asarray(centroids) - np.asarray(center), axis=1) <= radius
