# src/live/adaptive_grid_binance/config.py

# ==============================================================================
# 1. Default Strategy Parameters
# ==============================================================================
DEFAULT_STRATEGY_CONFIG = {
    # ----------------------------------------------------------------
    # 1. Basic Trading Parameters
    # ----------------------------------------------------------------
    "order_quantity": 50.0,
    "target_position": 0.0,
    "max_position": 1000.0,
    "min_position": -1000.0,
    # ----------------------------------------------------------------
    # 2. Grid Pricing Logic (Alpha)
    # ----------------------------------------------------------------
    # Skew Logic
    "inventory_skew_factor": 2.0,
    "trend_skew_factor": 7.0,
    "reversal_skew_factor": 10.0,
    # Spread Calculation
    "base_half_spread_bps": 10.0,
    "vol_half_spread_factor": 5.0,
    # ----------------------------------------------------------------
    # 3. Indicators & Signal Parameters
    # ----------------------------------------------------------------
    # Volatility
    "volatility_smoothing_factor": 0.1,
    # Trend (LLT)
    "trend_llt_windows": (60, 120, 240, 360, 480, 720, 960, 1440),
    # Reversal (LLT + RSI)
    "reversal_llt_windows": (60, 120, 240),
    "rsi_llt_window": 15,
    "rsi_windows": (60, 120, 240, 360),
    "rsi_lookback_window": 240,
    "rsi_oversold_threshold": 25.0,
    "rsi_overbought_threshold": 75.0,
    # ----------------------------------------------------------------
    # 4. Anchor Management
    # ----------------------------------------------------------------
    "anchor_decay_factor": 0.03,
    # ----------------------------------------------------------------
    # 5. Execution & Timer Intervals
    # ----------------------------------------------------------------
    "volatility_sample_interval_sec": 1.0,
    "grid_target_update_interval_sec": 1.0,
    "grid_update_threshold_bps": 2.0,
}

# ==============================================================================
# 2. Instrument-Specific Configurations
# ==============================================================================
INSTRUMENT_CONFIGS = {
    # "XAUUSDT": {
    #     "instrument_symbol": "XAUUSDT-PERP",
    #     "leverage": 5,
    #     "strategy_overrides": {
    #         "order_quantity": 0.002,
    #         "target_position": 0.0,
    #         "max_position": 0.04,
    #         "min_position": -0.04,
    #     },
    # },
    "DOGEUSDC": {
        "instrument_symbol": "DOGEUSDC-PERP",
        "leverage": 5,
        "strategy_overrides": {
            "order_quantity": 70,
            "target_position": 0,
            "max_position": 1400,
            "min_position": -1400,
        },
    },
    # "LINKUSDC": {
    #     "instrument_symbol": "LINKUSDC-PERP",
    #     "leverage": 5,
    #     "strategy_overrides": {
    #         "order_quantity": 1,
    #         "target_position": 10,
    #         "max_position": 30,
    #         "min_position": -10,
    #     },
    # },
}
