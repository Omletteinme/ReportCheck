import math

from src.agreement import auc, cohen_kappa, majority


def test_auc():
    assert auc([0.9, 0.8, 0.2, 0.1], [False, False, True, True]) == 1.0
    assert auc([0.5, 0.5], [False, True]) == 0.5
    assert math.isnan(auc([0.5, 0.6], [False, False]))


def test_cohen_kappa():
    assert cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0
    assert cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]) == -1.0
    assert abs(cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0])) < 1e-9  # agreement no better than chance
    assert math.isnan(cohen_kappa([0, 0, 0], [0, 0, 0]))


def test_majority_ties_flag_the_item():
    assert majority([[1, 0, 1], [1, 0, 0], [0, 0, 1], [1, 1, 0]]) == [1, 0, 1]  # 3/4, 1/4, 2/4
    assert majority([[1, 0], [0, 0]]) == [1, 0]
