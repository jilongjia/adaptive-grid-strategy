# src/indicators/basis.py

import math


class Basis:
    """
    追踪理论价格(Theoretical Price)与本地市场价格(Local Mid Price)之间的基差。
    Basis = Theoretical - Local
    使用 EWMA 进行平滑。
    """

    def __init__(self, alpha: float):
        if not (0 < alpha <= 1):
            raise ValueError("Alpha must be between 0 and 1.")

        self.alpha = alpha

        # --- State Variables ---
        self.value: float = 0.0
        self.initialized: bool = False

        # --- Warm-up Control ---
        self._warmup_countdown: int = math.ceil(1.0 / alpha)

    def update(self, theoretical_px: float, market_mid_px: float) -> None:
        """
        theoretical_px: 基于外部参考源计算出的理论价格 (如 IB/FX)
        market_mid_px: 本地市场的中间价 (Binance Mid)
        """
        # 1. 计算瞬时基差
        current_basis = theoretical_px - market_mid_px

        # 2. 如果是第一次更新，直接赋值
        if not self.initialized and self._warmup_countdown == math.ceil(
            1.0 / self.alpha
        ):
            self.value = current_basis
        else:
            # 3. EMA 平滑更新
            self.value = (self.alpha * current_basis) + (
                (1.0 - self.alpha) * self.value
            )

        # 4. 维护预热倒计时
        if not self.initialized:
            self._warmup_countdown -= 1
            if self._warmup_countdown <= 0:
                self.initialized = True
