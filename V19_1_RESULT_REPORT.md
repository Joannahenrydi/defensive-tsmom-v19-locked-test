# v19.1 Daily Starting-Point Robustness Report

## Decision

`V19_1_START_POINT_ROBUSTNESS_NOT_CONFIRMED`

The preliminary six-date test showed that one-month results depend on the starting date, so the
full experiment evaluated every eligible 2021–2024 trading day. All 984 cold-start episodes
completed. The overall distribution was positive and survived doubled transaction costs, but the
frozen cross-year stability gate failed because mean outcomes were negative for starts in both
2021 and 2022.

This is a post-OOS diagnostic on an already opened holdout. It is not a second pristine OOS test and
does not authorize live trading.

## Method

Each episode starts from cash on its decision date, retains all historical data required to compute
the unchanged causal v19 signal and covariance state, enters after that date's close, follows the
frozen 10-session rebalance schedule for 21 realized sessions and liquidates at the final close.
Entry, intermediate and exit costs are included. Adjacent episodes overlap, so inference uses a
fixed-seed moving-block bootstrap with 21-observation blocks rather than a naive t test.

## Overall distribution

| Metric | Baseline | 2× transaction cost |
|---|---:|---:|
| Episodes | 984 | 984 |
| Mean one-month return | **+0.0293%** | **+0.0191%** |
| Median one-month return | **+0.0338%** | **+0.0278%** |
| Positive episodes | **74.29%** | **70.22%** |
| 5th percentile | -0.1988% | -0.2183% |
| Worst episode | -0.5966% | -0.6126% |
| Best episode | +0.4770% | +0.4568% |

The 21-observation moving-block bootstrap estimated the mean at +0.0298%, with a 95% interval of
**+0.0030% to +0.0558%**. Thus, the aggregate mean remained positive after accounting for the
strong serial dependence caused by overlapping one-month windows.

## Starting-year stability

| Start year | Episodes | Mean | Median | Positive rate | 2× cost mean |
|---|---:|---:|---:|---:|---:|
| 2021 | 252 | **-0.0095%** | +0.0152% | 58.73% | -0.0234% |
| 2022 | 251 | **-0.0069%** | +0.0129% | 62.15% | -0.0136% |
| 2023 | 250 | +0.0548% | +0.0383% | 100.00% | +0.0492% |
| 2024 | 231 | +0.0834% | +0.0900% | 76.62% | +0.0687% |

The apparent contradiction between positive medians/win rates and negative means in 2021–2022 is
caused by clustered losing start dates with larger magnitude. For example, the worst episode began
2021-01-26 and lost 0.60% after liquidation. The best began 2024-08-20 and gained 0.48%.

Starting-month diagnostics also show clustering. February and September starts had negative mean
returns, and November's positive rate was 49.4%. These are descriptive patterns only; v19.1 does
not use them as a calendar filter.

## Frozen-gate outcome

Nine of ten gates passed:

- 984 completed episodes, zero failures and zero numerical-boundary solutions;
- overall mean, median and 74.29% positive rate passed;
- block-bootstrap lower bound was positive;
- doubled-cost mean and median were positive;
- **the every-start-year gate failed** because 2021 and 2022 means were below zero.

The evidence supports a modest positive aggregate starting-point effect, but not the stronger claim
that the strategy was reliably profitable regardless of when it began. The favorable aggregate is
materially driven by 2023–2024. The correct frozen conclusion is therefore “not confirmed,” without
changing the strategy or adding date filters after observing the result.

