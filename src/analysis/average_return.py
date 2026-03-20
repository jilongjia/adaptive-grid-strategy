import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class AverageReturn(PortfolioStatistic):
    """
    Average Return per completed round-trip trade (open -> close),
    calculated as the arithmetic mean of net returns based on notional value.

    Benchmark for grid strategies:
    - Must be > 0; negative values indicate spread captured does not cover fees and slippage.
    - Typical range: 0.0003 (3 bps) to 0.0030 (30 bps).
      Values above ~1% suggest grid spacing is too wide, trending toward swing rather than grid behavior.
    """

    @property
    def name(self) -> str:
        return "Average Return (Long and Ning)"

    def calculate_from_returns(self, returns: pd.Series) -> float:
        if returns is None or returns.empty:
            return 0.0

        return returns.mean()
