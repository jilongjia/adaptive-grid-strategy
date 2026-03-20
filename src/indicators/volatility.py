# src/indicators/volatility.py

import math


class Volatility:
    """
    基于 EWMA 的在线波动率计算。
    使用 None 作为未初始化状态，内置预热倒计时。
    """

    def __init__(self, alpha: float):
        if not (0 < alpha <= 1):
            raise ValueError("Alpha must be between 0 and 1.")

        self.alpha = alpha

        # --- State Variables ---
        self.last_price: float | None = None
        self.variance: float | None = None
        self.value: float | None = None
        self.initialized: bool = False

        # --- Warm-up Control ---
        self._warmup_countdown: int = math.ceil(1.0 / alpha)

    def update(self, price: float) -> None:
        # 1. 过滤无效价格
        if price <= 0:
            return

        # 2. [第一帧] 仅记录价格
        if self.last_price is None:
            self.last_price = price
            return

        log_ret = math.log(price / self.last_price)
        squared_ret = log_ret**2

        # 4. 更新方差
        if self.variance is None:
            self.variance = squared_ret
        else:
            self.variance = (self.alpha * squared_ret) + (
                (1.0 - self.alpha) * self.variance
            )

        # 5. 更新波动率数值
        self.value = math.sqrt(self.variance)
        self.last_price = price

        # 6. 维护预热倒计时
        if not self.initialized:
            self._warmup_countdown -= 1
            if self._warmup_countdown <= 0:
                self.initialized = True
