import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class MaxDrawdown(PortfolioStatistic):
    """
    Maximum drawdown of the equity curve, defined as the largest peak-to-trough
    decline relative to the running high watermark.
    Returns a negative float (e.g. -0.15 represents a 15% drawdown).

    Benchmark for grid strategies:
    - Safe:       > -0.10  — target range for conservative grid configurations.
    - Aggressive: -0.10 to -0.25 — acceptable for leveraged grids.
    - Warning:    < -0.30  — grid strategies recover slowly via high-frequency
      micro-profits; a drawdown of this magnitude typically indicates price has
      broken out of the grid range, with a high probability of strategy failure.
    """

    def __init__(self, initial_capital: float):
        super().__init__()
        if initial_capital <= 0:
            raise ValueError("Initial capital must be > 0")
        self._initial_capital = initial_capital

    @property
    def name(self) -> str:
        return "Max Drawdown (Long and Ning)"

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> float:
        if realized_pnls is None or realized_pnls.empty:
            return 0.0

        # 1. Build equity curve from cumulative PnL
        cumsum_pnl = realized_pnls.cumsum()
        equity_curve = self._initial_capital + cumsum_pnl

        # 2. Compute running peak; clipped to initial capital to handle early losses
        running_peak = equity_curve.cummax().clip(lower=self._initial_capital)

        # 3. Compute percentage drawdown at each point
        drawdown_pct = (equity_curve / running_peak) - 1.0

        # 4. Return the maximum drawdown (most negative value)
        return drawdown_pct.min()
