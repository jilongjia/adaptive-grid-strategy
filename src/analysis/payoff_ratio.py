import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


class PayoffRatio(PortfolioStatistic):
    """
    Payoff Ratio (盈亏收益比 / 赔率)
    Name ID: Payoff_Ratio_Jilong

    计算公式: 平均盈利 / 平均亏损的绝对值

    [网格交易建议标准]
    - 典型特征: 网格/HFT 策略的盈亏比通常较低，往往在 0.7 ~ 1.2 之间。
      * 与趋势策略(追求 >2.0)截然不同。网格策略倾向于"见好就收"(止盈近)，而止损通常较远。
      * 因此，"赚小钱、亏大钱"是网格的常态(例如：平均赚10U止盈，止损可能设在20U)。
    - 关键依赖:
      * 因为 Payoff Ratio 较低 (< 1.0)，策略必须拥有极高的胜率 (Win Rate > 60%) 才能实现正期望值。
    - 警示线:
      * 如果 Payoff Ratio < 0.5 (即亏一次需要赚两次才能补回)，
        除非胜率高达 75% 以上，否则策略极其脆弱，很容易因为连续几次止损导致净值大幅回撤。
    """

    @property
    def name(self) -> str:
        return "Payoff Ratio (Long and Ning)"

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> float:
        # 1. 基础检查
        if realized_pnls is None or realized_pnls.empty:
            return 0.0

        # 2. 分离盈利和亏损
        winning_trades = realized_pnls[realized_pnls > 0]
        losing_trades = realized_pnls[realized_pnls < 0]

        # 3. 边界情况处理
        if winning_trades.empty:
            return 0.0

        if losing_trades.empty:
            # 没有亏损交易，盈亏比理论无穷大
            return float("inf")

        # 4. 计算平均值
        avg_win = winning_trades.mean()
        avg_loss = losing_trades.abs().mean()

        # 5. 返回比率
        return avg_win / avg_loss
