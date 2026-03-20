# src/indicators/rsi.py

import math
from collections import deque


class RSI:
    """
    RSI indicator using Wilder's Smoothing, with rolling min/max tracking
    over a configurable lookback window.

    Initialization is managed by a dual-countdown mechanism:
    one for the initial SMA accumulation phase, and one for filling
    the lookback history buffer.
    """

    def __init__(self, window: int, lookback_window: int):
        self.window = window
        self.history = deque(maxlen=lookback_window)  # auto-evicts oldest entry

        # --- State (Wilder's Calculation) ---
        self.prev_value: float | None = None
        self.avg_gain: float = 0.0
        self.avg_loss: float = 0.0

        # --- Output ---
        self.value: float | None = None
        self.initialized: bool = False

        # --- Countdown Control (Dual Counters) ---
        # Counts down the first `window` ticks for SMA-based initialization
        self._calc_countdown: int = window
        # Counts down until the lookback buffer is fully populated;
        # only starts decrementing once RSI has a valid value
        self._history_countdown: int = lookback_window

    def update(self, price: float) -> None:
        if math.isnan(price):
            return

        # 1. First tick: record price only, no delta to compute
        if self.prev_value is None:
            self.prev_value = price
            return

        # 2. Compute price change
        delta = price - self.prev_value
        self.prev_value = price

        gain = delta if delta > 0 else 0.0
        loss = -delta if delta < 0 else 0.0

        # 3. Compute RSI value
        if self._calc_countdown > 0:
            # Phase A: accumulate gains/losses for SMA initialization
            self.avg_gain += gain
            self.avg_loss += loss
            self._calc_countdown -= 1

            if self._calc_countdown == 0:
                # Countdown complete: finalize initial averages and compute first RSI
                self.avg_gain /= self.window
                self.avg_loss /= self.window
                self._calculate_value()
        else:
            # Phase B: apply Wilder's smoothing on each subsequent tick
            self.avg_gain = (self.avg_gain * (self.window - 1) + gain) / self.window
            self.avg_loss = (self.avg_loss * (self.window - 1) + loss) / self.window
            self._calculate_value()

        # 4. Populate history buffer and check initialization
        if self.value is not None:
            self.history.append(self.value)

            if not self.initialized:
                if self._history_countdown > 0:
                    self._history_countdown -= 1

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
        """Returns the minimum RSI value within the lookback window."""
        if not self.history:
            return 50.0
        return min(self.history)

    @property
    def max_in_lookback(self) -> float:
        """Returns the maximum RSI value within the lookback window."""
        if not self.history:
            return 50.0
        return max(self.history)
