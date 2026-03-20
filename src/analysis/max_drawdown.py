import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class MaxDrawdown(PortfolioStatistic):
    """
    Max Drawdown (最大回撤)
    Name ID: Max_Drawdown_Jilong

    公式: (当前净值 - 历史最高净值) / 历史最高净值
    返回值: 负数浮点型 (例如 -0.15 代表回撤 15%)

    [网格交易建议标准]
    - 核心逻辑: 衡量账户资金承受的最大下行风险。
    - 典型范围:
      * 优秀 (Safe): > -0.10 (即回撤幅度小于 10%)。稳健型网格应以此为目标。
      * 正常 (Aggressive): -0.10 ~ -0.25。对于带杠杆的激进网格，这是常见区间。
    - 警示线:
      * 如果回撤幅度超过 -0.30 (30%)，对于网格策略属于"红色警报"。
        原因: 网格策略靠高频微利积累收益，填坑速度慢。深幅回撤通常意味着价格突破了网格区间(破网)，
        不仅资金受损，往往还伴随着严重的套牢仓位，策略失效的概率极高。
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

        # 1. 构建资金曲线 (Equity Curve)
        cumsum_pnl = realized_pnls.cumsum()
        equity_curve = self._initial_capital + cumsum_pnl

        # 2. 计算历史最高净值 (High Watermark)
        # clip 确保了基准线永远不会低于初始本金 (处理开局即亏损的情况)
        running_peak = equity_curve.cummax().clip(lower=self._initial_capital)

        # 3. 计算回撤百分比
        drawdown_pct = (equity_curve / running_peak) - 1.0

        # 4. 返回最大回撤 (最小的负数值)
        return drawdown_pct.min()
