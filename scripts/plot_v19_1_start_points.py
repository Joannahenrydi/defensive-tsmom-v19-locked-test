"""Plot the frozen v19.1 daily starting-point robustness results."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path("reports/v19_1_start_point")
FIGURES = ROOT / "figures"


def save(fig, name: str, pdf: PdfPages) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES / name, dpi=180, bbox_inches="tight")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(ROOT / "all_starting_points.csv.gz", parse_dates=["decision_session"])
    yearly = pd.read_csv(ROOT / "by_start_year.csv")
    monthly = pd.read_csv(ROOT / "by_start_month.csv")
    decision = json.loads((ROOT / "decision.json").read_text())
    net = data.liquidated_net_return * 100
    stress = data.double_transaction_cost_liquidated_net_return * 100

    with PdfPages(FIGURES / "v19_1_start_point_figures.pdf") as pdf:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        bins = np.linspace(min(net.min(), stress.min()), max(net.max(), stress.max()), 45)
        ax.hist(net, bins=bins, alpha=.65, label="Baseline", color="#375a7f")
        ax.hist(stress, bins=bins, alpha=.45, label="2× transaction cost", color="#c46a2d")
        ax.axvline(0, color="black", lw=.9)
        ax.set(title="984 cold-start one-month outcomes", xlabel="Liquidation-adjusted return (%)",
               ylabel="Starting points")
        ax.legend()
        save(fig, "01_return_distribution.png", pdf)

        fig, ax = plt.subplots(figsize=(11, 5.2))
        colors = np.where(net >= 0, "#2f7d5c", "#b33a3a")
        ax.scatter(data.decision_session, net, c=colors, s=10, alpha=.7)
        ax.axhline(0, color="black", lw=.8)
        ax.set(title="One-month return by starting date", ylabel="Liquidation-adjusted return (%)")
        ax.grid(alpha=.2)
        save(fig, "02_return_by_start_date.png", pdf)

        rolling = data.set_index("decision_session").liquidated_net_return.rolling(63).mean() * 100
        fig, ax = plt.subplots(figsize=(11, 5.2))
        ax.plot(rolling, color="#375a7f")
        ax.axhline(0, color="black", lw=.8)
        ax.set(title="63-starting-point rolling mean", ylabel="Mean return (%)")
        ax.grid(alpha=.25)
        save(fig, "03_rolling_mean.png", pdf)

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
        x = np.arange(len(yearly))
        axes[0].bar(x - .18, yearly.mean_return * 100, width=.36, label="Mean", color="#375a7f")
        axes[0].bar(x + .18, yearly.median_return * 100, width=.36, label="Median", color="#7f9db9")
        axes[0].axhline(0, color="black", lw=.8)
        axes[0].set_xticks(x, yearly.start_year)
        axes[0].set(title="Return by starting year", ylabel="Return (%)")
        axes[0].legend()
        axes[1].bar(yearly.start_year.astype(str), yearly.positive_rate * 100, color="#2f7d5c")
        axes[1].axhline(50, color="black", ls="--", label="50% yearly gate")
        axes[1].set(title="Positive-episode rate by year", ylabel="Positive (%)", ylim=(0, 105))
        axes[1].legend()
        save(fig, "04_start_year_robustness.png", pdf)

        fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        axes[0].bar(monthly.start_month, monthly.mean_return * 100,
                    color=np.where(monthly.mean_return >= 0, "#2f7d5c", "#b33a3a"))
        axes[0].axhline(0, color="black", lw=.8)
        axes[0].set(title="Mean return by starting month", ylabel="Mean (%)")
        axes[1].bar(monthly.start_month, monthly.positive_rate * 100, color="#375a7f")
        axes[1].axhline(50, color="black", ls="--")
        axes[1].set(xlabel="Calendar month", ylabel="Positive (%)", xticks=range(1, 13))
        save(fig, "05_start_month_robustness.png", pdf)

        frame = data.assign(year=data.decision_session.dt.year,
                            month=data.decision_session.dt.month)
        heat = frame.pivot_table(index="year", columns="month",
                                 values="liquidated_net_return", aggfunc="mean").reindex(columns=range(1,13))
        fig, ax = plt.subplots(figsize=(11, 4.5))
        bound = max(abs(heat.min().min()), abs(heat.max().max())) * 100
        image = ax.imshow(heat * 100, cmap="RdYlGn", aspect="auto", vmin=-bound, vmax=bound)
        ax.set_xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        ax.set_yticks(range(len(heat.index)), heat.index)
        ax.set_title("Mean one-month return by starting year and month (%)")
        for y in range(len(heat.index)):
            for x in range(12):
                value = heat.iloc[y, x]
                if pd.notna(value):
                    ax.text(x, y, f"{value*100:.2f}", ha="center", va="center", fontsize=8)
        fig.colorbar(image, ax=ax, shrink=.8)
        save(fig, "06_year_month_heatmap.png", pdf)

        ordered = np.sort(net.to_numpy())
        ecdf = np.arange(1, len(ordered) + 1) / len(ordered)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(ordered, ecdf * 100, color="#375a7f")
        ax.axvline(0, color="black", lw=.8)
        ax.set(title="Empirical distribution of starting-point returns",
               xlabel="Liquidation-adjusted return (%)", ylabel="Cumulative probability (%)")
        ax.grid(alpha=.25)
        save(fig, "07_empirical_cdf.png", pdf)

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.scatter(data.turnover * 100, net, s=12, alpha=.55, color="#6b6b9a")
        ax.axhline(0, color="black", lw=.8)
        ax.set(title="Turnover versus one-month return", xlabel="Episode turnover (%)",
               ylabel="Liquidation-adjusted return (%)")
        ax.grid(alpha=.2)
        save(fig, "08_turnover_vs_return.png", pdf)

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist(data.max_drawdown * 100, bins=40, color="#b33a3a", alpha=.75)
        ax.set(title="Within-episode maximum drawdown distribution",
               xlabel="Maximum drawdown (%)", ylabel="Starting points")
        save(fig, "09_episode_drawdowns.png", pdf)

        expanding = data.liquidated_net_return.expanding().mean() * 100
        lower = decision["block_bootstrap"]["lower_95"] * 100
        upper = decision["block_bootstrap"]["upper_95"] * 100
        fig, ax = plt.subplots(figsize=(11, 5.2))
        ax.plot(data.decision_session, expanding, color="#375a7f", label="Expanding mean")
        ax.axhspan(lower, upper, color="#2f7d5c", alpha=.18,
                   label="Final 21-block bootstrap 95% CI")
        ax.axhline(0, color="black", lw=.8)
        ax.set(title="Expanding starting-point mean and block-bootstrap interval",
               ylabel="Mean return (%)")
        ax.legend()
        ax.grid(alpha=.2)
        save(fig, "10_expanding_mean_bootstrap.png", pdf)


if __name__ == "__main__":
    main()

