# src/indicators/rsi.py

import math
from collections import deque


class RSI:
    """
    RSI 指标 (Wilder's Smoothing) + 历史极值记录 (Rolling Min/Max).

    使用双倒计时机制管理初始化状态。
    """

    def __init__(self, window: int, lookback_window: int):
        self.window = window
        # maxlen 自动处理溢出，保持固定长度
        self.history = deque(maxlen=lookback_window)

        # --- State (Wilder's Calculation) ---
        self.prev_value: float | None = None
        self.avg_gain: float = 0.0
        self.avg_loss: float = 0.0

        # --- Output ---
        self.value: float | None = None
        self.initialized: bool = False

        # --- Countdown Control (Dual Counters) ---
        # 1. 计算倒计时：负责前 window 个点的 SMA 累加
        self._calc_countdown: int = window
        # 2. 缓存倒计时：负责填满 lookback_window 个点的历史数据
        # 注意：只有当 RSI 算出数值后，这个倒计时才开始工作
        self._history_countdown: int = lookback_window

    def update(self, price: float) -> None:
        if math.isnan(price):
            return

        # 1. 记录第一个点
        if self.prev_value is None:
            self.prev_value = price
            return

        # 2. 计算变动
        delta = price - self.prev_value
        self.prev_value = price

        gain = delta if delta > 0 else 0.0
        loss = -delta if delta < 0 else 0.0

        # 3. 计算 RSI (基于 _calc_countdown 分支)
        if self._calc_countdown > 0:
            # [阶段 A]: 累加阶段 (SMA 初始化)
            self.avg_gain += gain
            self.avg_loss += loss

            self._calc_countdown -= 1

            # 刚好倒计时结束，计算初始平均值和第一个 RSI 值
            if self._calc_countdown == 0:
                self.avg_gain /= self.window
                self.avg_loss /= self.window
                self._calculate_value()
        else:
            # [阶段 B]: 迭代阶段 (Wilder's Smoothing)
            # 倒计时结束后，直接进入此分支，不再进行减法判断
            self.avg_gain = (self.avg_gain * (self.window - 1) + gain) / self.window
            self.avg_loss = (self.avg_loss * (self.window - 1) + loss) / self.window
            self._calculate_value()

        # 4. 维护历史与最终初始化状态
        # 只有当 RSI 计算出有效值时，才开始填充历史
        if self.value is not None:
            self.history.append(self.value)

            # 只有未完成初始化时，才检查历史倒计时
            if not self.initialized:
                if self._history_countdown > 0:
                    self._history_countdown -= 1

                # 当历史数据也填满时，彻底完成初始化
                if self._history_countdown == 0:
                    self.initialized = True

    def _calculate_value(self) -> None:
        if self.avg_loss == 0:
            self.value = 100.0
        elif self.avg_gain == 0:
            self.value = 0.0
        else:
            rs = self.avg_gain / self.avg_loss
            self.value = 100.0 - (100.0 / (1.0 + rs))

    @property
    def min_in_lookback(self) -> float:
        """返回过去 N 个周期内的最低 RSI"""
        if not self.history:
            return 50.0
        return min(self.history)

    @property
    def max_in_lookback(self) -> float:
        """返回过去 N 个周期内的最高 RSI"""
        if not self.history:
            return 50.0
        return max(self.history)
