import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class AverageReturn(PortfolioStatistic):
    """
    Average Return (平均收益率)
    Name ID: Average_Return_Jilong

    公式: returns.mean()
    定义: 基于(名义本金)的单笔完整交易(Open->Close)的扣费后净收益率。

    [网格交易建议标准]
    - 核心要求: 必须 > 0。如果 < 0，说明捕捉的价差覆盖不了手续费和滑点。
    - 典型范围: 0.0003 (3bps) ~ 0.0030 (30bps)。
      * 网格策略通常捕捉微小的均值回归，单笔收益率不会很高。
      * 主要是靠高频次的累积。如果数值过高(如 >1%)，说明网格间距过大，属于波段策略而非典型高频网格。
    """

    @property
    def name(self) -> str:
        return "Average Return (Long and Ning)"

    def calculate_from_returns(self, returns: pd.Series) -> float:
        if returns is None or returns.empty:
            return 0.0

        # 直接计算算术平均值
        return returns.mean()
