import numpy as np
import pytest

from src.anatomy import GROUPS, HULL, REGION_NODES, orientation, region_anchors, select_parts


def box(center, size=0.04, n=40, seed=0):
    rng = np.random.default_rng(seed)
    return np.asarray(center, dtype=float) + rng.uniform(-size / 2, size / 2, (n, 3))


# canonical frame: x = patient's left, y = up, z = anterior
CANON = {"brain": (0, 1.6, 0), "pelvis": (0, 0.9, 0), "lung_l": (0.1, 1.3, 0), "lung_r": (-0.1, 1.3, 0),
         "heart": (0.03, 1.28, 0.05), "spine": (0, 1.3, -0.08)}


def in_frame(r_new_from_old):
    """Express canonical landmarks in a dataset frame whose axes are r_old = r_new_from_old.T @ new."""
    back = r_new_from_old.T
    return {k: back @ np.array(v, dtype=float) for k, v in CANON.items()}


def test_orientation_recovers_canonical_frame_from_permuted_and_flipped_axes():
    # dataset frame: x = anterior, y = right, z = down  (new = R @ old with R below)
    r = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], dtype=float)  # left <- -y, up <- -z, anterior <- x
    assert np.linalg.det(r) > 0
    c = in_frame(r)
    got = orientation(c)
    assert np.allclose(got, r)
    for k, v in CANON.items():
        assert np.allclose(got @ c[k], v)


def test_orientation_identity_when_already_canonical():
    assert np.allclose(orientation({k: np.array(v, dtype=float) for k, v in CANON.items()}), np.eye(3))


def test_orientation_rejects_mirrored_labels():
    c = {k: np.array(v, dtype=float) for k, v in CANON.items()}
    c["lung_l"], c["lung_r"] = c["lung_r"], c["lung_l"]  # left/right swapped in the data
    with pytest.raises(ValueError):
        orientation(c)


def test_select_parts_matches_exact_names_case_insensitively_and_reports_missing():
    names = {"Heart": "BP1", "left lung": "BP2", "left first rib": "BP3", "right first rib": "BP4", "skin": "BP5"}
    found, missing = select_parts(names, {"heart": ["heart"], "ribs": ["left first rib", "right first rib", "left second rib"],
                                          "skin": ["SKIN"]})
    assert found["heart"] == [("Heart", "BP1")] and found["skin"] == [("skin", "BP5")]
    assert [i for _, i in found["ribs"]] == ["BP3", "BP4"] and missing == ["left second rib"]


def test_groups_cover_every_node_used_by_regions():
    for nodes in REGION_NODES.values():
        for n in nodes:
            assert n.removesuffix(HULL) in GROUPS


def test_lung_regions_highlight_the_lobe_tree_and_its_shell():
    assert REGION_NODES["lung-r-upper"] == ["lung_r_upper", "lung_r_upper_hull"]
    assert REGION_NODES["pleura-l"] == ["lung_l_upper", "lung_l_upper_hull", "lung_l_lower", "lung_l_lower_hull"]
    assert REGION_NODES["heart"] == ["heart"]


def synthetic_body():
    return {
        "lung_r_upper": box((-0.09, 1.38, 0.0), seed=1), "lung_r_mid": box((-0.09, 1.30, 0.02), seed=2),
        "lung_r_lower": box((-0.09, 1.20, 0.0), seed=3), "lung_l_upper": box((0.09, 1.38, 0.0), seed=4),
        "lung_l_lower": box((0.09, 1.20, 0.0), seed=5), "heart": box((0.03, 1.28, 0.05), seed=6),
        "airway": box((0, 1.45, 0), size=0.02, seed=7), "aorta": box((0.0, 1.34, 0.0), seed=8),
        "diaphragm": box((0, 1.10, 0), size=0.1, seed=9), "ribs": box((0, 1.28, 0), size=0.3, seed=10),
        "sternum": box((0, 1.3, 0.08), seed=11), "clavicles": box((0, 1.42, 0.05), size=0.2, seed=12),
        "spine": box((0, 1.25, -0.08), size=0.5, seed=13), "liver": box((-0.06, 1.05, 0.02), seed=14),
        "stomach": box((0.06, 1.05, 0.02), seed=15), "brain": box((0, 1.68, 0), seed=16),
        "skull": box((0, 1.68, 0), seed=17), "pelvis": box((0, 0.9, 0), seed=18),
    }


def test_region_anchors_land_on_the_right_side_and_height():
    a = region_anchors(synthetic_body())
    assert set(a) == set(REGION_NODES)
    x = lambda rid: a[rid]["anchor"][0]  # noqa: E731
    y = lambda rid: a[rid]["anchor"][1]  # noqa: E731
    assert x("lung-r-upper") < 0 < x("lung-l-upper")             # patient's right is negative x
    assert y("lung-r-upper") > y("lung-r-mid") > y("lung-r-lower")
    assert y("lung-l-upper") > y("lung-l-mid") > y("lung-l-lower")
    assert x("pleura-r") < x("lung-r-lower") and x("pleura-l") > x("lung-l-lower")  # lateral edge
    assert x("ribs") < 0                                       # right side of the rib cage
    assert y("head") > y("neck") > y("heart") > y("abdomen") > y("pelvis")
    assert a["spine"]["anchor"][2] < a["heart"]["anchor"][2]    # spine behind the heart
    assert a["lung-l-mid"]["nodes"] == ["lung_l_upper", "lung_l_upper_hull", "lung_l_lower", "lung_l_lower_hull"]


def test_keep_near_drops_far_pieces():
    from src.anatomy import keep_near

    cents = np.array([[0, 0, 0], [0.05, 0.1, 0], [0, -0.2, 0]])
    assert keep_near(cents, np.array([0, 0.03, 0]), 0.165).tolist() == [True, True, False]


def test_limb_bones_are_in_the_model_but_not_in_any_region():
    assert {"arm_bones", "leg_bones"} <= set(GROUPS)
    assert any("femur" in n for n in GROUPS["leg_bones"]) and any("humerus" in n for n in GROUPS["arm_bones"])
    used = {n.removesuffix(HULL) for nodes in REGION_NODES.values() for n in nodes}
    assert not used & {"arm_bones", "leg_bones"}
