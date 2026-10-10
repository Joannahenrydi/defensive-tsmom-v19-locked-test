"""Create the complete v19 locked-test figure set from committed result tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path("reports/locked_test")
FIGURES = ROOT / "figures"
TEST_START = pd.Timestamp("2021-01-04")


def save(fig, name: str, pdf: PdfPages) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES / name, dpi=180, bbox_inches="tight")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(ROOT / "baseline_daily.csv", parse_dates=["session"], index_col="session").loc[TEST_START:]
    stress = pd.read_csv(ROOT / "double_cost_daily.csv", parse_dates=["session"], index_col="session").loc[TEST_START:]
    weights = pd.read_csv(ROOT / "baseline_weights.csv.gz", parse_dates=[0], index_col=0).loc[TEST_START:]
    yearly = pd.read_csv(ROOT / "yearly_attribution.csv")
    sleeves = pd.read_csv(ROOT / "sleeve_attribution.csv")
    assets = pd.read_csv(ROOT / "asset_attribution.csv")
    legs = pd.read_csv(ROOT / "long_short_attribution.csv")
    regimes = pd.read_csv(ROOT / "drawdown_regime_attribution.csv")

    nav = (1 + base.net_return).cumprod()
    stress_nav = (1 + stress.net_return).cumprod()
    drawdown = nav / nav.cummax() - 1
    monthly = (1 + base.net_return).groupby(base.index.to_period("M")).prod() - 1

    with PdfPages(FIGURES / "v19_locked_test_figures.pdf") as pdf:
        fig, ax = plt.subplots(figsize=(10, 5.5))
        ax.plot(nav, label="Baseline net", lw=2)
        ax.plot(stress_nav, label="Frozen trades, 2× transaction cost", lw=1.6, ls="--")
        ax.axhline(1, color="black", lw=.8)
        ax.set(title="v19 locked-test net growth (2021–2024)", ylabel="Growth of $1")
        ax.legend()
        ax.grid(alpha=.25)
        save(fig, "01_net_growth.png", pdf)

        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.fill_between(drawdown.index, drawdown.values * 100, 0, color="#b33a3a", alpha=.7)
        ax.axhline(-20, color="black", ls="--", label="Frozen -20% gate")
        ax.set(title="v19 locked-test drawdown", ylabel="Drawdown (%)")
        ax.legend()
        ax.grid(alpha=.25)
        save(fig, "02_drawdown.png", pdf)

        fig, ax = plt.subplots(figsize=(8.5, 5))
        colors = np.where(yearly.net_return >= 0, "#2f7d5c", "#b33a3a")
        ax.bar(yearly.year.astype(str), yearly.net_return * 100, color=colors)
        ax.axhline(0, color="black", lw=.8)
        ax.set(title="Calendar-year net returns", ylabel="Return (%)")
        for i, value in enumerate(yearly.net_return * 100):
            ax.text(i, value + (.35 if value >= 0 else -.65), f"{value:.2f}%", ha="center")
        save(fig, "03_calendar_returns.png", pdf)

        grid = monthly.to_frame("return")
        grid["year"] = grid.index.year
        grid["month"] = grid.index.month
        pivot = grid.pivot(index="year", columns="month", values="return").reindex(columns=range(1, 13))
        fig, ax = plt.subplots(figsize=(11, 4.2))
        image = ax.imshow(pivot * 100, cmap="RdYlGn", aspect="auto", vmin=-3, vmax=3)
        ax.set_xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        ax.set_yticks(range(len(pivot.index)), pivot.index)
        ax.set_title("Monthly net-return heatmap (%)")
        for y in range(len(pivot.index)):
            for x in range(12):
                value = pivot.iloc[y, x]
                if pd.notna(value):
                    ax.text(x, y, f"{value*100:.1f}", ha="center", va="center", fontsize=8)
        fig.colorbar(image, ax=ax, shrink=.8)
        save(fig, "04_monthly_heatmap.png", pdf)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(base.gross * 100, label="Gross exposure", lw=1.4)
        ax.plot(base.net * 100, label="Net exposure", lw=1.2)
        ax.set(title="Portfolio exposure", ylabel="Exposure (%)")
        ax.legend()
        ax.grid(alpha=.25)
        save(fig, "05_exposure.png", pdf)

        fig, ax = plt.subplots(figsize=(8.5, 5))
        table = sleeves.sort_values("gross_return_contribution")
        ax.barh(table.sleeve, table.gross_return_contribution * 100,
                color=np.where(table.gross_return_contribution >= 0, "#2f7d5c", "#b33a3a"))
        ax.axvline(0, color="black", lw=.8)
        ax.set(title="Gross contribution by sleeve", xlabel="Additive contribution (%)")
        save(fig, "06_sleeve_attribution.png", pdf)

        top = pd.concat([assets.nlargest(7, "gross_return_contribution"),
                         assets.nsmallest(7, "gross_return_contribution")]).drop_duplicates("symbol")
        top = top.sort_values("gross_return_contribution")
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(top.symbol, top.gross_return_contribution * 100,
                color=np.where(top.gross_return_contribution >= 0, "#2f7d5c", "#b33a3a"))
        ax.axvline(0, color="black", lw=.8)
        ax.set(title="Largest ETF contributors and detractors", xlabel="Additive contribution (%)")
        save(fig, "07_asset_attribution.png", pdf)

        fig, axes = plt.subplots(1, 2, figsize=(10, 4.8))
        axes[0].bar(legs.leg, legs.gross_return_contribution * 100,
                    color=["#2f7d5c", "#b33a3a"])
        axes[0].axhline(0, color="black", lw=.8)
        axes[0].set(title="Long/short gross contribution", ylabel="Contribution (%)")
        axes[1].bar(legs.leg, legs.average_gross_exposure * 100,
                    color=["#2f7d5c", "#6b6b9a"])
        axes[1].set(title="Average long/short gross exposure", ylabel="Exposure (%)")
        save(fig, "08_long_short.png", pdf)

        rolling_mean = base.net_return.rolling(63).mean() * 252
        rolling_vol = base.net_return.rolling(63).std() * np.sqrt(252)
        rolling_sharpe = rolling_mean / rolling_vol.replace(0, np.nan)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(rolling_sharpe, color="#375a7f")
        ax.axhline(0, color="black", lw=.8)
        ax.set(title="63-session rolling net Sharpe", ylabel="Annualized Sharpe")
        ax.grid(alpha=.25)
        save(fig, "09_rolling_sharpe.png", pdf)

        fig, ax = plt.subplots(figsize=(9, 5))
        ordered = regimes.sort_values("gross_return_contribution")
        ax.barh(ordered.regime, ordered.gross_return_contribution * 100,
                color=np.where(ordered.gross_return_contribution >= 0, "#2f7d5c", "#b33a3a"))
        ax.axvline(0, color="black", lw=.8)
        ax.set(title="Gross contribution by lagged SPY drawdown regime",
               xlabel="Additive contribution (%)")
        save(fig, "10_regime_attribution.png", pdf)


if __name__ == "__main__":
    main()
