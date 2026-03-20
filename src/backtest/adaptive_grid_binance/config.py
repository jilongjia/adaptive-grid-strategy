# src/backtest/binance_adaptive_grid/config.py

import pandas as pd

# ==============================================================================
# 1. 交易标的与时间 (Trading Context)
# ==============================================================================
# 仅指定 Symbol，不包含 Venue
INSTRUMENT_SYMBOL = "DOGEUSDT-PERP"

# 初始资金 (USDT)
INITIAL_CAPITAL = 1_000.0

# 回测时间段
BACKTEST_START = pd.Timestamp("2024-03-15 00:00:00", tz="UTC")
BACKTEST_END = pd.Timestamp("2024-03-30 23:59:59", tz="UTC")

# ==============================================================================
# 2. 策略参数 (Strategy Parameters)
# ==============================================================================
STRATEGY_CONFIG = {
    # --- Basic ---
    "order_quantity": 50.0,
    "target_position": 0.0,
    "max_position": 1000.0,
    "min_position": -1000.0,
    # --- Pricing Alpha ---
    "base_half_spread_bps": 50.0,
    "vol_half_spread_factor": 30.0,
    # Skew Factors
    "inventory_skew_factor": 0.0,
    "trend_skew_factor": 30.0,
    "reversal_skew_factor": 30.0,
    # --- Indicators ---
    "volatility_smoothing_factor": 0.05,
    "trend_llt_windows": (60, 120, 240, 360, 480, 720, 960, 1440),
    "reversal_llt_windows": (60, 120, 240),
    "rsi_llt_window": 15,
    "rsi_windows": (60, 120, 240, 480, 960, 1920),
    "rsi_lookback_window": 240,
    "rsi_oversold_threshold": 25.0,
    "rsi_overbought_threshold": 75.0,
    # --- Anchor Management---
    "anchor_decay_factor": 0.001,
    # --- Intervals ---
    "volatility_sample_interval_sec": 1.0,
    "grid_target_update_interval_sec": 1.0,
    "grid_update_threshold_bps": 2.0,
}
