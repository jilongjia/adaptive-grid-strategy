import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class ProfitFactor(PortfolioStatistic):
    """
    Total gross profit divided by total gross loss (absolute value).

    Benchmark for grid strategies:
    - Acceptable: > 1.2 — values between 1.0 and 1.1 leave little buffer against
      slippage and fee variation in live trading.
    - Good:       > 1.5
    - Excellent:  > 2.0
    - Note: high-frequency grid strategies rely on turnover volume rather than a
      high per-trade ratio; a profit factor of 1.3 can still generate strong
      annualized returns given sufficient trade count.
    """

    @property
    def name(self) -> str:
        return "Profit Factor (Long and Ning)"

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> float:
        if realized_pnls is None or realized_pnls.empty:
            return 0.0

        gross_profit = realized_pnls[realized_pnls > 0].sum()
        gross_loss = abs(realized_pnls[realized_pnls <= 0].sum())

        if gross_loss == 0:
            if gross_profit > 0:
                return float("inf")  # No losing trades
            return 0.0  # No trades or all flat

        return gross_profit / gross_loss
