import numpy as np
import pandas as pd
from nautilus_trader.analysis.statistic import PortfolioStatistic


# ==============================================================================
# 系统质量数 (SQN - System Quality Number)
# ==============================================================================
class SystemQualityNumber(PortfolioStatistic):
    """
    System Quality Number (SQN)
    Name ID: SQN_Jilong

    公式: sqrt(N) * (Avg Return / Std Return)
    来源: Van Tharp. 衡量系统“容易获利”的程度。

    [网格交易建议标准]
    - ⚠️ HFT 特别警示:
      SQN 对交易次数(N)非常敏感。因为网格策略的 N 通常极大(成千上万)，
      所以不能使用传统的低频策略标准(即 >3.0 优秀, >7.0 圣杯)。

    - 针对 HFT/网格的修订标准 (扣费后):
      * 及格线: > 5.0。
        由于 N 很大，如果 SQN 还是很低，说明 (Avg/Std) 也就是单笔盈亏比率极差，
        利润几乎全被手续费吃掉了。
      * 优秀: > 10.0。
        这代表策略在极高的交易频率下，依然保持了很强的稳定性。
      * 极值: > 20.0 或更高。
        在短期高频回测中常见，代表极度平滑的资金曲线。

    - 核心解读:
      SQN 本质上是 "交易频率" 和 "单笔锐度" 的乘积。
      对于网格策略，如果 SQN 下降，通常意味着波动率(Std)变大，即网格被"破网"的风险在增加。
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

        # 防御标准差为 0 (通常发生在只有 1 笔交易或所有交易收益完全相同时)
        if std_ret == 0:
            return 0.0

        return np.sqrt(num) * (avg_ret / std_ret)
