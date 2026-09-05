"""Evaluate proxy-drift benchmark predictions from JSONL.

Usage:
    python research/experiments/evaluate_binary.py \
        --input research/datasets/example.jsonl \
        --methods naive static context

The evaluator intentionally uses only the Python standard library so the
benchmark can run in minimal CI environments.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Metrics:
    method: str
    n: int
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float | None
    recall: float | None
    f1: float | None
    fpr: float | None
    fnr: float | None


def _safe_div(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            row = json.loads(raw)
            required = {"scenario_id", "scenario_family", "source_class", "ground_truth_drift", "predictions"}
            missing = sorted(required - row.keys())
            if missing:
                raise ValueError(f"line {line_no}: missing required fields: {missing}")
            if not isinstance(row["ground_truth_drift"], bool):
                raise ValueError(f"line {line_no}: ground_truth_drift must be boolean")
            if not isinstance(row["predictions"], dict):
                raise ValueError(f"line {line_no}: predictions must be an object")
            rows.append(row)
    if not rows:
        raise ValueError("input contains no benchmark rows")
    return rows


def evaluate(rows: Iterable[dict], method: str) -> Metrics:
    tp = fp = tn = fn = 0
    n = 0
    for row in rows:
        if method not in row["predictions"]:
            raise ValueError(f"scenario {row['scenario_id']}: missing prediction for method {method!r}")
        pred = row["predictions"][method]
        if not isinstance(pred, bool):
            raise ValueError(f"scenario {row['scenario_id']}: prediction for {method!r} must be boolean")
        truth = row["ground_truth_drift"]
        n += 1
        if truth and pred:
            tp += 1
        elif not truth and pred:
            fp += 1
        elif not truth and not pred:
            tn += 1
        else:
            fn += 1

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return Metrics(
        method=method,
        n=n,
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        fpr=_safe_div(fp, fp + tn),
        fnr=_safe_div(fn, fn + tp),
    )


def fmt(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{value:.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--methods", nargs="+", required=True)
    parser.add_argument("--source-class", choices=["synthetic", "controlled", "real_world"])
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    rows = load_rows(args.input)
    if args.source_class:
        rows = [row for row in rows if row["source_class"] == args.source_class]
        if not rows:
            raise ValueError(f"no rows for source class {args.source_class!r}")

    results = [evaluate(rows, method) for method in args.methods]

    print("method\tn\ttp\tfp\ttn\tfn\tprecision\trecall\tf1\tfpr\tfnr")
    for item in results:
        print(
            "\t".join(
                [
                    item.method,
                    str(item.n),
                    str(item.tp),
                    str(item.fp),
                    str(item.tn),
                    str(item.fn),
                    fmt(item.precision),
                    fmt(item.recall),
                    fmt(item.f1),
                    fmt(item.fpr),
                    fmt(item.fnr),
                ]
            )
        )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps([asdict(item) for item in results], indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
