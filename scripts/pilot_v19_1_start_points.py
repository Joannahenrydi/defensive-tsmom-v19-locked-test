"""Pilot a few deterministic v19.1 starting dates before authorizing the full grid."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from strategy.v19 import FROZEN_CALIBRATION_SLOPE, build_defensive_tsmom, load_data
from strategy.v19_1 import run_starting_point

PILOT_DATES = [
    pd.Timestamp("2021-01-04"),
    pd.Timestamp("2021-11-01"),
    pd.Timestamp("2022-03-01"),
    pd.Timestamp("2022-09-01"),
    pd.Timestamp("2023-04-03"),
    pd.Timestamp("2024-01-02"),
]


def main() -> None:
    output = Path("reports/v19_1_start_point")
    output.mkdir(parents=True, exist_ok=True)
    data = load_data(Path("inputs/etf_daily.csv"))
    score = build_defensive_tsmom(data)["sizing_score"] * FROZEN_CALIBRATION_SLOPE
    table = pd.DataFrame(run_starting_point(date, score, data) for date in PILOT_DATES)
    table.to_csv(output / "pilot_start_points.csv", index=False)
    completed = table.loc[table.status.eq("COMPLETED"), "net_return"]
    summary = {
        "pilot_dates": [str(date.date()) for date in PILOT_DATES],
        "completed_episodes": int(len(completed)),
        "unique_returns_at_12_decimals": int(completed.round(12).nunique()),
        "return_standard_deviation": float(completed.std(ddof=1)),
        "return_range": float(completed.max() - completed.min()),
        "full_grid_is_meaningful": bool(len(completed) == len(PILOT_DATES)
                                        and completed.round(12).nunique() > 1
                                        and np.isfinite(completed).all()),
    }
    (output / "pilot_decision.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(table[["decision_session", "net_return", "max_drawdown", "turnover"]].to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

