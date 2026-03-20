# src/indicators/basis.py

import math


class Basis:
    """
    Tracks the basis between a theoretical price and a local market mid price.
    Basis = Theoretical - Local. Smoothed via EWMA.
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
        Args:
            theoretical_px: Reference price derived from an external source (e.g. IB/FX).
            market_mid_px:  Local market mid price (e.g. Binance mid).
        """
        # 1. Compute instantaneous basis
        current_basis = theoretical_px - market_mid_px

        # 2. First update: seed directly without smoothing
        if not self.initialized and self._warmup_countdown == math.ceil(
            1.0 / self.alpha
        ):
            self.value = current_basis
        else:
            # 3. Apply EWMA smoothing
            self.value = (self.alpha * current_basis) + (
                (1.0 - self.alpha) * self.value
            )

        # 4. Advance warmup countdown
        if not self.initialized:
            self._warmup_countdown -= 1
            if self._warmup_countdown <= 0:
                self.initialized = True
