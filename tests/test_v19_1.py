import pandas as pd
from pathlib import Path

from strategy.v19 import FROZEN_CALIBRATION_SLOPE, build_defensive_tsmom, load_data
from strategy.v19_1 import HOLDING_SESSIONS, run_starting_point


def test_cold_start_trades_at_start_and_measures_following_21_sessions():
    data = load_data(Path("inputs/etf_daily.csv"))
    score = build_defensive_tsmom(data)["sizing_score"] * FROZEN_CALIBRATION_SLOPE
    start = pd.Timestamp("2021-01-04")
    result = run_starting_point(start, score, data)
    calendar = data["returns"].index
    position = calendar.get_loc(start)
    assert result["status"] == "COMPLETED"
    assert result["first_realized_session"] == calendar[position + 1]
    assert result["last_realized_session"] == calendar[position + HOLDING_SESSIONS]
    assert result["rebalance_count"] == 3
