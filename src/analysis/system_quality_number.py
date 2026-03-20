import numpy as np
import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class SystemQualityNumber(PortfolioStatistic):
    """
    System Quality Number (SQN) as defined by Van Tharp.
    Formula: sqrt(N) * (mean return / std return).

    Benchmark for grid strategies:
    - SQN scales with trade count (N), so traditional thresholds (> 3.0 good,
      > 7.0 excellent) do not apply to high-frequency grid strategies.
    - Revised thresholds for HFT/grid (post-fee):
      * Acceptable: > 5.0
      * Good:       > 10.0 — strong consistency maintained at high trade frequency.
      * Excellent:  > 20.0 — common in short-term backtests with very smooth equity curves.
    - A declining SQN typically signals increasing return volatility (std), which
      often indicates the grid range is being breached.
    """

    @property
    def name(self) -> str:
        return "SQN (Long and Ning)"

    def calculate_from_returns(self, returns: pd.Series) -> float:
        if returns is None or returns.empty:
            return 0.0

        num = len(returns)
        avg_ret = returns.mean()
        std_ret = returns.std()

        # Guard against zero std (single trade or all returns identical)
        if std_ret == 0:
            return 0.0

        return np.sqrt(num) * (avg_ret / std_ret)
