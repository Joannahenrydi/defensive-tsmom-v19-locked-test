"""Run every eligible 2021-2024 v19.1 cold-start one-month episode."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from strategy.v19 import FROZEN_CALIBRATION_SLOPE, LOCKED_TEST, build_defensive_tsmom, load_data, sha256
from strategy.v19_1 import HOLDING_SESSIONS, run_starting_point

PROTOCOL = Path("docs/V19_1_START_POINT_PROTOCOL.md")
SOURCE = Path("inputs/etf_daily.csv")
OUTPUT = Path("reports/v19_1_start_point")
BOOTSTRAP_SEED = 1901
BOOTSTRAP_REPS = 5000
BLOCK_LENGTH = 21

_DATA = None
_SCORE = None


def initialize_worker(source: str) -> None:
    global _DATA, _SCORE
    _DATA = load_data(Path(source))
    _SCORE = build_defensive_tsmom(_DATA)["sizing_score"] * FROZEN_CALIBRATION_SLOPE


def run_worker(date: str) -> dict:
    return run_starting_point(pd.Timestamp(date), _SCORE, _DATA)


def moving_block_bootstrap(values: np.ndarray) -> dict:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    count = len(values)
    blocks = int(np.ceil(count / BLOCK_LENGTH))
    max_start = count - BLOCK_LENGTH
    means = np.empty(BOOTSTRAP_REPS)
    for iteration in range(BOOTSTRAP_REPS):
        starts = rng.integers(0, max_start + 1, size=blocks)
        sample = np.concatenate([values[start:start + BLOCK_LENGTH] for start in starts])[:count]
        means[iteration] = sample.mean()
    lower, upper = np.quantile(means, [.025, .975])
    return {"seed": BOOTSTRAP_SEED, "replications": BOOTSTRAP_REPS,
            "block_length": BLOCK_LENGTH, "mean": float(means.mean()),
            "lower_95": float(lower), "upper_95": float(upper)}


def distribution(series: pd.Series) -> dict:
    return {
        "count": int(series.count()),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "standard_deviation": float(series.std(ddof=1)),
        "positive_rate": float(series.gt(0).mean()),
        "loss_rate": float(series.lt(0).mean()),
        "minimum": float(series.min()),
        "p05": float(series.quantile(.05)),
        "p25": float(series.quantile(.25)),
        "p75": float(series.quantile(.75)),
        "p95": float(series.quantile(.95)),
        "maximum": float(series.max()),
    }


def main(workers: int) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    calendar = pd.read_csv(SOURCE, usecols=["date", "symbol"], parse_dates=["date"])
    sessions = pd.DatetimeIndex(sorted(calendar.loc[calendar.symbol.eq("SPY"), "date"].unique()))
    test_sessions = sessions[(sessions >= LOCKED_TEST[0]) & (sessions <= LOCKED_TEST[1])]
    dates = test_sessions[:-HOLDING_SESSIONS]
    with ProcessPoolExecutor(max_workers=workers, initializer=initialize_worker,
                             initargs=(str(SOURCE),)) as executor:
        rows = []
        for number, row in enumerate(executor.map(run_worker, [str(date.date()) for date in dates],
                                                  chunksize=8), start=1):
            rows.append(row)
            if number % 100 == 0:
                print(f"completed {number}/{len(dates)} episodes", flush=True)
    table = pd.DataFrame(rows).sort_values("decision_session").reset_index(drop=True)
    table.to_csv(OUTPUT / "all_starting_points.csv.gz", index=False, compression="gzip")
    completed = table.loc[table.status.eq("COMPLETED")].copy()
    completed["start_year"] = pd.to_datetime(completed.decision_session).dt.year
    completed["start_month"] = pd.to_datetime(completed.decision_session).dt.month
    metric = "liquidated_net_return"
    stress_metric = "double_transaction_cost_liquidated_net_return"
    overall = distribution(completed[metric])
    stress = distribution(completed[stress_metric])
    bootstrap = moving_block_bootstrap(completed[metric].to_numpy())

    yearly = completed.groupby("start_year").agg(
        episodes=(metric, "size"), mean_return=(metric, "mean"), median_return=(metric, "median"),
        positive_rate=(metric, lambda x: x.gt(0).mean()), minimum=(metric, "min"),
        maximum=(metric, "max"), mean_double_cost=(stress_metric, "mean"),
    ).reset_index()
    monthly = completed.groupby("start_month").agg(
        episodes=(metric, "size"), mean_return=(metric, "mean"), median_return=(metric, "median"),
        positive_rate=(metric, lambda x: x.gt(0).mean()),
    ).reset_index()
    yearly.to_csv(OUTPUT / "by_start_year.csv", index=False)
    monthly.to_csv(OUTPUT / "by_start_month.csv", index=False)

    completed["expanding_mean"] = completed[metric].expanding().mean()
    completed[["decision_session", "expanding_mean"]].to_csv(
        OUTPUT / "expanding_mean.csv", index=False
    )
    best = completed.nlargest(20, metric)
    worst = completed.nsmallest(20, metric)
    best.to_csv(OUTPUT / "best_20_starting_points.csv", index=False)
    worst.to_csv(OUTPUT / "worst_20_starting_points.csv", index=False)

    failures = int(table.status.ne("COMPLETED").sum())
    boundary = int(completed.numerical_boundary_solutions.sum())
    yearly_gate = bool(((yearly.mean_return > 0) & (yearly.median_return > 0)
                        & (yearly.positive_rate >= .50)).all())
    gates = {
        "at_least_750_completed_episodes": len(completed) >= 750,
        "zero_failed_episodes": failures == 0,
        "zero_numerical_boundary_solutions": boundary == 0,
        "overall_mean_positive": overall["mean"] > 0,
        "overall_median_positive": overall["median"] > 0,
        "overall_positive_rate_at_least_55pct": overall["positive_rate"] >= .55,
        "every_start_year_passes": yearly_gate,
        "block_bootstrap_lower_95_positive": bootstrap["lower_95"] > 0,
        "double_cost_mean_positive": stress["mean"] > 0,
        "double_cost_median_positive": stress["median"] > 0,
    }
    passed = bool(all(gates.values()))
    decision = {
        "status": ("V19_1_START_POINT_ROBUSTNESS_CONFIRMED" if passed
                   else "V19_1_START_POINT_ROBUSTNESS_NOT_CONFIRMED"),
        "post_oos_diagnostic": True,
        "orders_allowed": False,
        "protocol_sha256": sha256(PROTOCOL),
        "source_sha256": sha256(SOURCE),
        "episode_holding_sessions": HOLDING_SESSIONS,
        "candidate_starting_points": int(len(dates)),
        "completed_episodes": int(len(completed)),
        "failed_episodes": failures,
        "numerical_boundary_solutions": boundary,
        "overall": overall,
        "double_transaction_cost": stress,
        "block_bootstrap": bootstrap,
        "gates": gates,
    }
    (OUTPUT / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    main(args.workers)

