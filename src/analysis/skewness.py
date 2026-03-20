import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class Skewness(PortfolioStatistic):
    """
    Third standardized moment of trade returns.

    Benchmark for grid strategies:
    - Grid and arbitrage strategies almost always exhibit negative skew: most trades
      close at small take-profit levels (right side of distribution), while the long
      tail sits on the left (occasional large losses).
    - Normal range: -2.0 to -0.5.
    - Warning:      < -3.0 indicates extreme left-tail risk; individual loss events
      can be catastrophic despite a high overall win rate.
    - Contrast: trend-following strategies typically show positive skew (small losses,
      large wins).
    """

    @property
    def name(self) -> str:
        return "Skewness (Long and Ning)"

    def calculate_from_returns(self, returns: pd.Series) -> float:
        # Requires at least 3 samples for a meaningful third moment
        if returns is None or len(returns) < 3:
            return 0.0

        # pandas skew() uses the unbiased estimator by default
        return returns.skew()
