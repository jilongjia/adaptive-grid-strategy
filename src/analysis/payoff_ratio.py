import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class PayoffRatio(PortfolioStatistic):
    """
    Average win divided by average loss (absolute value).

    Benchmark for grid strategies:
    - Typical range: 0.7 to 1.2 — unlike trend-following strategies, grid strategies
      take profit quickly and hold losers longer, so a sub-1.0 ratio is expected.
    - A low payoff ratio demands a high win rate to maintain positive expectancy;
      a ratio below 0.5 requires a win rate above ~75% to avoid significant drawdowns.
    """

    @property
    def name(self) -> str:
        return "Payoff Ratio (Long and Ning)"

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> float:
        if realized_pnls is None or realized_pnls.empty:
            return 0.0

        winning_trades = realized_pnls[realized_pnls > 0]
        losing_trades = realized_pnls[realized_pnls < 0]

        if winning_trades.empty:
            return 0.0

        if losing_trades.empty:
            # No losing trades: ratio is theoretically infinite
            return float("inf")

        avg_win = winning_trades.mean()
        avg_loss = losing_trades.abs().mean()

        return avg_win / avg_loss
