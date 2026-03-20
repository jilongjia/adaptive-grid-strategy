import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class ProfitFactor(PortfolioStatistic):
    """
    Profit Factor (获利因子)
    Name ID: Profit_Factor_Jilong

    公式: 总盈利金额 / |总亏损金额|

    [网格交易建议标准]
    - 核心逻辑: 衡量策略每亏损 1 块钱，能赚回多少钱。这是扣除手续费后的"净获利能力"。
    - 典型范围:
      * 及格: > 1.2。因为网格策略有"左尾风险"(Skewness为负)，需要足够的盈余缓冲。
        如果 PF 在 1.0 ~ 1.1 之间，实盘稍有滑点或费率波动就会变成亏损。
      * 优秀: > 1.5。
      * 极佳: > 2.0。
    - HFT 特性:
      * 高频策略依靠"高周转"赚钱，Profit Factor 不需要像趋势策略那样动辄 3.0 或 4.0。
      * 只要交易次数足够多(大数定律)，1.3 的 Profit Factor 也能产生巨额的年化回报。
    """

    @property
    def name(self) -> str:
        return "Profit Factor (Long and Ning)"

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> float:
        if realized_pnls is None or realized_pnls.empty:
            return 0.0

        # 分离盈利和亏损
        gross_profit = realized_pnls[realized_pnls > 0].sum()
        gross_loss = abs(realized_pnls[realized_pnls <= 0].sum())

        # 处理分母为0的情况 (无亏损交易)
        if gross_loss == 0:
            if gross_profit > 0:
                return float("inf")  # 完美盈利
            return 0.0  # 无交易或全平

        return gross_profit / gross_loss
