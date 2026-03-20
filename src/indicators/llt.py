# src/indicators/llt.py


class LLT:
    """
    Low-Lag Trendline (LLT): a second-order low-lag filter for trend estimation.
    """

    def __init__(self, window: int):
        self.window = window
        self.alpha = 2.0 / (window + 1)

        # --- Pre-computed Coefficients ---
        a = self.alpha
        self.c_p0 = a - (a**2) / 4.0
        self.c_p1 = (a**2) / 2.0
        self.c_p2 = -(a - 0.75 * (a**2))
        self.c_l1 = 2 * (1 - a)
        self.c_l2 = -((1 - a) ** 2)

        # --- State Variables ---
        self.price_prev1: float | None = None
        self.price_prev2: float | None = None
        self.llt_prev1: float | None = None
        self.llt_prev2: float | None = None

        self.value: float | None = None
        self.slope: float | None = None
        self.initialized: bool = False

        # --- Warm-up Control ---
        self._warmup_countdown: int = window / 2

    def update(self, price: float) -> None:
        # 1. Reject invalid prices
        if price <= 0:
            return

        # 2. Update filter state

        # [Case 1] First tick: initialize state, no slope available yet
        if self.price_prev1 is None:
            self.price_prev1 = price
            self.llt_prev1 = price
            self.value = price

        # [Case 2] Second tick: compute first slope against previous value
        elif self.price_prev2 is None:
            self.price_prev2 = self.price_prev1
            self.price_prev1 = price
            self.llt_prev2 = self.llt_prev1
            self.llt_prev1 = price
            self.slope = price - self.value
            self.value = price

        # [Case 3] Third tick onward: apply full LLT recurrence
        else:
            new_llt = (
                self.c_p0 * price
                + self.c_p1 * self.price_prev1
                + self.c_p2 * self.price_prev2
                + self.c_l1 * self.llt_prev1
                + self.c_l2 * self.llt_prev2
            )

            self.slope = new_llt - self.llt_prev1

            # Roll state forward
            self.price_prev2 = self.price_prev1
            self.price_prev1 = price
            self.llt_prev2 = self.llt_prev1
            self.llt_prev1 = new_llt
            self.value = new_llt

        # 3. Advance warmup countdown
        if not self.initialized:
            self._warmup_countdown -= 1
            if self._warmup_countdown <= 0:
                self.initialized = True

    @property
    def slope_direction(self) -> int:
        """
        Returns the direction of the current slope: 1 (up), -1 (down), or 0 (flat/unknown).
        """
        if self.slope is None:
            return 0

        if self.slope > 0:
            return 1
        elif self.slope < 0:
            return -1
        return 0
