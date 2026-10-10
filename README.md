# v19 Defensive TSMOM — Locked Test

This repository contains one frozen strategy and its prespecified 2021–2024 locked-test protocol.
It intentionally excludes every other research version.

> **Status: `V19_LOCKED_TEST_PASSED`.** The frozen candidate retained positive net CAGR and
> Sharpe in the 2021–2024 holdout and passed the frozen double-transaction-cost stress. The edge
> was weak and concentrated; paper and live orders remain disabled.

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

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m scripts.run_locked_test
MPLCONFIGDIR=/tmp/mplconfig python -m scripts.plot_locked_test
```

The committed result is the sole authorized holdout read. Reproduction verifies it; it is not a
license to change the strategy and rescore the same holdout.

Historical backtests are research evidence, not a guarantee of future performance. Paper and live
orders remain disabled.
