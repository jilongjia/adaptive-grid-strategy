import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


# ==============================================================================
# 8. 峰度 (Kurtosis)
# ==============================================================================
class Kurtosis(PortfolioStatistic):
    """
    Kurtosis (峰度 - 超额峰度)
    Name ID: Kurtosis_Jilong

    Formula: Fisher's definition (Excess Kurtosis). Normal Distribution = 0.

    [网格交易建议标准]
    - 典型特征: 网格策略通常具有极高的峰度 (通常 > 8.0，甚至 > 20.0)。
      * 这是因为网格策略的大量交易都终结于预设的止盈点，导致收益率分布在均值附近极度"尖锐"。
    - 警示信号:
      * 如果 Kurtosis 极高 (如 > 10)，且 Skewness 为负数 (如 < -1.0):
        这是最危险的"推土机模式"——平时表现极其稳定(尖峰)，但隐含着极为罕见却毁灭性的暴仓风险(肥尾)。
      * 此时必须进行极端的压力测试(Stress Test)。
    """

    @property
    def name(self) -> str:
        return "Kurtosis (Long and Ning)"

    def calculate_from_returns(self, returns: pd.Series) -> float:
        # 计算四阶矩至少需要 4 个样本点才能得出有统计意义的结果
        if returns is None or len(returns) < 4:
            return 0.0

        return returns.kurt()
