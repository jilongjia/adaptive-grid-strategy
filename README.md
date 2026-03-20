# Adaptive Grid Strategy

A market-making system built on [NautilusTrader](https://nautilustrader.io/). The strategy places a single bid and ask at dynamically computed prices, updating them continuously based on real-time volatility, trend, and mean-reversion signals.

---

## How It Works

The core idea is to quote around an **anchor price** — a slowly decaying EMA of the mid price that resets hard on every fill — rather than around the raw market mid. This makes the grid resistant to short-term noise while remaining responsive to genuine price shifts.

**Reservation price** is computed as:

```
reservation_px = anchor_px + trend_skew + reversal_skew
```

**Half-spread** is computed as:

```
half_spread = base_half_spread + vol × vol_half_spread_factor
```

**Inventory skew** is applied as a one-sided offset: if the strategy is long, the bid is pushed down; if short, the ask is pushed up. This passively reduces exposure without crossing the spread.

### Signals

| Signal | Indicator | Role |
|---|---|---|
| Trend | LLT (Low-Lag Trendline) ensemble | Skews quotes in the trend direction |
| Reversal | Short-window LLT + RSI ensemble | Fades overbought/oversold conditions |
| Volatility | EWMA of squared log returns | Scales spread width dynamically |

### Order Management

- One GTC post-only limit order per side at all times.
- Orders are modified in place when the target price drifts beyond a configurable threshold (default: 2 bps). This minimises cancel/replace round-trips.
- On fill: anchor resets to fill price, inventory ratio updates, and new targets are computed immediately.

---

## Project Structure

```
src/
├── strategies/
│   └── adaptive_grid.py        # Strategy core: pricing logic, order management
│
├── indicators/
│   ├── llt.py                  # Low-Lag Trendline (second-order filter)
│   ├── rsi.py                  # RSI with Wilder's smoothing + rolling min/max
│   ├── volatility.py           # EWMA volatility estimator
│   └── basis.py                # Theoretical vs local price basis tracker
│
├── live/
│   └── adaptive_grid_binance/
│       ├── config.py           # Default parameters + per-instrument overrides
│       └── run.py              # Node setup and strategy registration for live trading
│
├── backtest/
│   └── binance_adaptive_grid/
│       ├── config.py           # Backtest date range, capital, and strategy parameters
│       └── run.py              # Backtest engine setup and fill statistics report
│
└── analysis/
    ├── average_return.py       # Mean net return per round-trip
    ├── win_rate.py             # Fraction of profitable trades
    ├── payoff_ratio.py         # Avg win / avg loss
    ├── profit_factor.py        # Gross profit / gross loss
    ├── max_drawdown.py         # Peak-to-trough equity drawdown
    ├── skewness.py             # Third moment of return distribution
    ├── kurtosis.py             # Excess kurtosis (Fisher's definition)
    └── system_quality_number.py  # SQN: sqrt(N) × (mean / std)
```

---

## Installation

**Requirements:** Python 3.11+, a running Rust toolchain (required by NautilusTrader).

```bash
# Clone the repository
git clone https://github.com/your-username/adaptive-grid-strategy.git
cd adaptive-grid-strategy

# Create and activate a virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv sync
```

### Environment Variables (Live Trading)

Create a `.env` file in the project root:

```env
BINANCE_MOMENTUM_RISK_PARITY_GRID_API_KEY=your_api_key
BINANCE_MOMENTUM_RISK_PARITY_GRID_API_SECRET=your_api_secret
```

---

## Running a Backtest

1. Edit `src/backtest/binance_adaptive_grid/config.py` to set the instrument, date range, capital, and strategy parameters.
2. Ensure historical bar data is available in the Parquet catalog at `catalog/`.
3. Run:

```bash
python -m backtest.binance_adaptive_grid.run
```

The engine prints a fill statistics summary on completion:

```
=============================================
>>> Fill Statistics
Total fills       : 18432
Total notional    : 9,842,105.34 USDT
  Buy             : 4,921,388.12 USDT
  Sell            : 4,920,717.22 USDT
Capital turnover  : 9842.11%
=============================================
```

## Running Live

1. Edit `src/live/adaptive_grid_binance/config.py` to configure active instruments and parameter overrides.
2. Set API credentials in `.env`.
3. Run:

```bash
python -m live.adaptive_grid_binance.run
```

---

## Key Configuration Parameters

| Parameter | Description |
|---|---|
| `base_half_spread_bps` | Minimum half-spread regardless of volatility |
| `vol_half_spread_factor` | Volatility multiplier for spread scaling |
| `trend_skew_factor` | Weight of trend signal on reservation price |
| `reversal_skew_factor` | Weight of mean-reversion signal on reservation price |
| `inventory_skew_factor` | Aggressiveness of inventory-reducing skew |
| `anchor_decay_factor` | EMA alpha for anchor drift toward market mid |
| `grid_update_threshold_bps` | Minimum price move before modifying an order |

---

## Dependencies

- [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) — execution, backtesting, and data infrastructure
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment variable management