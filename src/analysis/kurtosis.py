import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class Kurtosis(PortfolioStatistic):
    """
    Excess kurtosis of trade returns (Fisher's definition, normal distribution = 0).

    Benchmark for grid strategies:
    - Typical range: > 8.0, often > 20.0. Grid strategies concentrate returns near
      a fixed take-profit level, producing a sharply peaked distribution.
    - Warning: high kurtosis (> 10) combined with negative skewness (< -1.0) is the
      classic "steamroller" profile — stable returns punctuated by rare but catastrophic
      drawdowns. Stress testing is essential in this case.
    """

    @property
    def name(self) -> str:
        return "Kurtosis (Long and Ning)"

    def calculate_from_returns(self, returns: pd.Series) -> float:
        # Requires at least 4 samples for a statistically meaningful fourth moment
        if returns is None or len(returns) < 4:
            return 0.0

        return returns.kurt()
