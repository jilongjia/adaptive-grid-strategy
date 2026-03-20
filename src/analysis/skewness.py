import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


# ==============================================================================
# 7. 偏度 (Skewness)
# ==============================================================================
class Skewness(PortfolioStatistic):
    """
    Skewness (偏度)
    Name ID: Skewness_Jilong

    Formula: Third standardized moment of returns.

    [网格交易建议标准]
    - 典型特征: 网格/套利策略几乎总是呈现"负偏度" (Negative Skew, < 0)。
      * 这里的逻辑是：大多数交易都是小额止盈(分布在右侧均值附近)，而长尾都在左侧(少数的大额止损)。
    - 警示线:
      * 正常区间: -2.0 ~ -0.5。
      * 危险区间: < -3.0。这意味着策略存在极端的"左尾风险" (Left-tail risk)。
        虽然胜率可能很高，但一旦发生亏损，其破坏力是毁灭性的。
    - 对比:
      * 趋势策略通常是正偏 (>0)，即"亏小赚大"。
    """

    @property
    def name(self) -> str:
        return "Skewness (Long and Ning)"

    def calculate_from_returns(self, returns: pd.Series) -> float:
        # 计算偏度至少需要 3 个样本点才能得出有意义的三阶矩
        if returns is None or len(returns) < 3:
            return 0.0

        # Pandas 的 skew() 默认计算无偏估计
        return returns.skew()
