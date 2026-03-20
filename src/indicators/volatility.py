# src/indicators/volatility.py

import math


class Volatility:
    """
    Online volatility estimator based on EWMA of squared log returns.
    Uses None as the uninitialized sentinel and an internal warmup countdown.
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
        # 1. Reject invalid prices
        if price <= 0:
            return

        # 2. First tick: record price only, no return to compute
        if self.last_price is None:
            self.last_price = price
            return

        log_ret = math.log(price / self.last_price)
        squared_ret = log_ret**2

        # 3. Update EWMA variance
        if self.variance is None:
            self.variance = squared_ret
        else:
            self.variance = (self.alpha * squared_ret) + (
                (1.0 - self.alpha) * self.variance
            )

        # 4. Derive volatility from variance
        self.value = math.sqrt(self.variance)
        self.last_price = price

        # 5. Advance warmup countdown
        if not self.initialized:
            self._warmup_countdown -= 1
            if self._warmup_countdown <= 0:
                self.initialized = True
