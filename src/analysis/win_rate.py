import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class WinRate(PortfolioStatistic):
    """
    Fraction of trades with strictly positive net profit after fees.
    Breakeven trades (PnL == 0) are counted as losses.

    Benchmark for grid strategies:
    - Grid strategies rely on high win rate to compensate for a sub-1.0 payoff ratio.
    - Normal range: 60% to 80%.
    - Warning: < 55% is typically the loss threshold for grid strategies given their
      characteristically low payoff ratio.
    - Note: breakeven trades are intentionally excluded from winners — in HFT,
      zero-profit trades still consume execution resources and opportunity cost.
    """

    @property
    def name(self) -> str:
        return "Win Rate (Long and Ning)"

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> float:
        if realized_pnls is None or realized_pnls.empty:
            return 0.0

        num_trades = len(realized_pnls)
        num_winners = (realized_pnls > 0).sum()

        return num_winners / num_trades
