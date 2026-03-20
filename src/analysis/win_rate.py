import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class WinRate(PortfolioStatistic):
    """
    Win Rate (胜率)
    Name ID: Win_Rate_Jilong

    公式: 盈利交易次数 / 总交易次数
    定义: 扣费后净利润严格大于 0 的交易占比。

    [网格交易建议标准]
    - 核心逻辑: 网格/HFT 策略的"生命线"。
      * 网格策略的本质是"大概率赚小钱，小概率亏大钱"。
    - 典型范围:
      * 正常: 60% ~ 80%。
      * 极高: > 85%。某些高频套利策略可以达到此数值。
    - 警示线:
      * < 55%: 对于网格策略来说，这通常是亏损的红线。
      * 原因: 由于网格策略的 Payoff Ratio (盈亏比) 通常较低 (< 1.0)，
        必须依靠 > 60% 甚至更高的胜率才能维持正的数学期望值。
    - 0值处理:
      * 此算法将 PnL=0 (盈亏平衡) 视为"未盈利"。
      * 对于 HFT 这是一个好的严苛标准，因为无效交易也消耗了系统资源和机会成本。
    """

    @property
    def name(self) -> str:
        return "Win Rate (Long and Ning)"

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> float:
        if realized_pnls is None or realized_pnls.empty:
            return 0.0

        # 1. 获取总交易次数
        num_trades = len(realized_pnls)

        # 2. 获取盈利次数
        num_winners = (realized_pnls > 0).sum()

        # 3. 计算胜率
        return num_winners / num_trades
