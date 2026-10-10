# v19 Defensive TSMOM — Locked Test

This repository contains one frozen strategy and its prespecified 2021–2024 locked-test protocol.
It intentionally excludes every other research version.

> **Status: `V19_LOCKED_TEST_PASSED`.** The frozen candidate retained positive net CAGR and
> Sharpe in the 2021–2024 holdout and passed the frozen double-transaction-cost stress. The edge
> was weak and concentrated; paper and live orders remain disabled.

> **v19.1 post-OOS diagnostic: `V19_1_START_POINT_ROBUSTNESS_NOT_CONFIRMED`.** The
> overall one-month starting-point distribution was positive, but 2021 and 2022 starting dates had
> negative mean returns, so the frozen every-year stability gate failed.

The source strategy was frozen after train (2008–2016) and reused development (2017–2020). The
locked test is 2021-01-04 through 2024-12-31. See
[`docs/V19_LOCKED_TEST_PROTOCOL.md`](docs/V19_LOCKED_TEST_PROTOCOL.md).

## Locked-test result

| Evaluation | Net CAGR | Net Sharpe | Max DD | Worst month |
|---|---:|---:|---:|---:|
| Baseline | **0.51%** | **0.150** | **-11.03%** | **-2.92%** |
| Same trades, 2× transaction cost | **0.50%** | **0.147** | **-11.03%** | **-2.92%** |

The result passed the deliberately minimal directional-survival gate, but it was much weaker than
train (Sharpe 1.210) and development (Sharpe 0.927). Return correlation to SPY was 0.732 and the top
five ETFs represented 78.0% of absolute contribution. The conclusion is positive survival, not a
strong or fully diversified CTA result.

- [Full result report](LOCKED_TEST_RESULT_REPORT.md)
- [Complete figure set](RESULT_FIGURES.md)
- [Machine-readable decision](reports/locked_test/decision.json)
- [Integrity audit](reports/locked_test/integrity_audit.json)

## v19.1 arbitrary starting-point diagnostic

Every eligible 2021–2024 trading day was treated as the start of a new cash account. Each of 984
episodes traded the unchanged v19 strategy for 21 realized sessions and then liquidated.

| Metric | Baseline | 2× transaction cost |
|---|---:|---:|
| Mean one-month return | **+0.0293%** | **+0.0191%** |
| Median | **+0.0338%** | **+0.0278%** |
| Positive episodes | **74.29%** | **70.22%** |
| Worst episode | -0.5966% | -0.6126% |

The aggregate distribution and 21-observation block bootstrap were positive, but mean returns for
2021 and 2022 starts were -0.0095% and -0.0069%. The result therefore does not support the stronger
claim that v19 was profitable regardless of starting date.

- [v19.1 protocol](docs/V19_1_START_POINT_PROTOCOL.md)
- [v19.1 result report](V19_1_RESULT_REPORT.md)
- [v19.1 complete figure set](V19_1_RESULT_FIGURES.md)
- [v19.1 machine-readable decision](reports/v19_1_start_point/decision.json)

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m scripts.run_locked_test
MPLCONFIGDIR=/tmp/mplconfig python -m scripts.plot_locked_test
python -m scripts.pilot_v19_1_start_points
python -m scripts.run_v19_1_start_point_robustness --workers 4
MPLCONFIGDIR=/tmp/mplconfig python -m scripts.plot_v19_1_start_points
```

The committed result is the sole authorized holdout read. Reproduction verifies it; it is not a
license to change the strategy and rescore the same holdout.

Historical backtests are research evidence, not a guarantee of future performance. Paper and live
orders remain disabled.
