"""Parse the result files that the paper figures are drawn from (so charts never carry hand-typed numbers)."""
import re

_ROW = re.compile(r"^\|\s*(?P<name>[^|]+?)\s*\|\s*(?P<a>-?\d+\.\d+)\s*\|\s*(?P<b>-?\d+\.\d+)\s*\|\s*(?P<d>[+-]\d+\.\d+)\s*"
                  r"\((?P<lo>[+-]\d+\.\d+) to (?P<hi>[+-]\d+\.\d+)\)\s*\|$")
_AUC_ROW = re.compile(r"^\|\s*(?P<name>[^|]+?)\s*\|\s*(?P<auc>\d\.\d+)\s*\|\s*(?P<pos>\d+)\s*\|$")
_AUC_LINE = re.compile(r"AUC (?P<name>.+?)\s+(?P<auc>\d\.\d+)\s+\(95% CI (?P<lo>\d\.\d+)-(?P<hi>\d\.\d+), positives=(?P<pos>\d+)\)")
_SET = re.compile(r"^== (?P<name>.+?): n=(?P<n>\d+)")


def parse_summary(md: str) -> dict:
    """{'metrics': {name: {plain, best, diff, lo, hi}}, 'auc_plain': {name: {auc, positives}}, 'reports': int}."""
    metrics, auc = {}, {}
    for line in md.splitlines():
        if m := _ROW.match(line):
            metrics[m["name"]] = {"plain": float(m["a"]), "best": float(m["b"]), "diff": float(m["d"]),
                                  "lo": float(m["lo"]), "hi": float(m["hi"])}
        elif m := _AUC_ROW.match(line):
            auc[m["name"]] = {"auc": float(m["auc"]), "positives": int(m["pos"])}
    reports = re.search(r"\((?:final|heldout|set2), (\d+) reports\)", md)
    return {"metrics": metrics, "auc_plain": auc, "reports": int(reports[1]) if reports else 0}


def parse_auc(txt: str) -> dict:
    """{'set name': {'n': int, 'checks': {'total vs any error': {auc, lo, hi, positives}}}} from eval_verifier.py output."""
    sets, current = {}, None
    for line in txt.splitlines():
        if m := _SET.match(line):
            current = m["name"]
            sets[current] = {"n": int(m["n"]), "checks": {}}
        elif current and (m := _AUC_LINE.search(line)):
            sets[current]["checks"][m["name"]] = {"auc": float(m["auc"]), "lo": float(m["lo"]), "hi": float(m["hi"]),
                                                  "positives": int(m["pos"])}
    return sets
