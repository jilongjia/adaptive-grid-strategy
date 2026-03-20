# src/backtest/binance_adaptive_grid/run.py

import pandas as pd
from nautilus_trader.adapters.binance import BINANCE, BINANCE_VENUE
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.models import FillModel, LatencyModel
from nautilus_trader.backtest.node import BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.persistence.config import DataCatalogConfig

from analysis import (
    AverageReturn,
    Kurtosis,
    MaxDrawdown,
    PayoffRatio,
    ProfitFactor,
    Skewness,
    SystemQualityNumber,
    WinRate,
)
from backtest.adaptive_grid_binance.config import (
    BACKTEST_END,
    BACKTEST_START,
    INITIAL_CAPITAL,
    INSTRUMENT_SYMBOL,
    STRATEGY_CONFIG,
)
from strategies.adaptive_grid import AdaptiveGridStrategy, AdaptiveGridStrategyConfig


def run_backtest():
    # ==========================================================================
    # 0. Infrastructure Configuration
    # ==========================================================================
    CATALOG_PATH = "catalog"

    FILL_PROBABILITY = 0.2
    FILL_SEED = 11
    LATENCY_NANOS = 10_000_000  # 10ms

    LOG_CONFIG = LoggingConfig(
        log_level="WARNING",
        log_level_file="INFO",
        log_directory="logs",
        log_file_name="binance_adaptive_grid_backtest",
        log_file_max_size=300_000_000,
        log_file_max_backup_count=100,
    )

    # ==========================================================================
    # 1. Data Loading & Instrument Setup
    # ==========================================================================
    catalog = ParquetDataCatalog(CATALOG_PATH)

    VENUE = BINANCE
    instrument_id = InstrumentId.from_str(f"{INSTRUMENT_SYMBOL}.{VENUE}")

    instruments = catalog.instruments(instrument_ids=[instrument_id])
    if not instruments:
        raise ValueError(f"Instrument {instrument_id} not found in catalog.")
    instrument = instruments[0]

    # ==========================================================================
    # 2. Engine & Venue Configuration
    # ==========================================================================
    engine_config = BacktestEngineConfig(
        logging=LOG_CONFIG,
        catalogs=[DataCatalogConfig(path=CATALOG_PATH)],
    )
    engine = BacktestEngine(config=engine_config)

    fill_model = FillModel(
        prob_fill_on_limit=FILL_PROBABILITY,
        random_seed=FILL_SEED,
    )
    latency_model = LatencyModel(base_latency_nanos=LATENCY_NANOS)

    engine.add_venue(
        venue=BINANCE_VENUE,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        starting_balances=[Money(INITIAL_CAPITAL, instrument.quote_currency)],
        latency_model=latency_model,
        fill_model=fill_model,
        bar_execution=False,
        liquidity_consumption=True,
    )
    engine.add_instrument(instrument)

    # ==========================================================================
    # 3. Strategy Configuration
    # ==========================================================================
    strategy_config = AdaptiveGridStrategyConfig(
        instrument_id=instrument.id, **STRATEGY_CONFIG
    )
    strategy = AdaptiveGridStrategy(strategy_config)
    engine.add_strategy(strategy=strategy)

    # ==========================================================================
    # 4. Analysis Statistics Registration
    # ==========================================================================
    statistics = [
        AverageReturn(),
        WinRate(),
        PayoffRatio(),
        ProfitFactor(),
        MaxDrawdown(INITIAL_CAPITAL),
        Skewness(),
        Kurtosis(),
        SystemQualityNumber(),
    ]
    for stat in statistics:
        engine.portfolio.analyzer.register_statistic(stat)

    # ==========================================================================
    # 5. Run Backtest
    # ==========================================================================
    try:
        engine.run(start=BACKTEST_START, end=BACKTEST_END)

        fills_raw = engine.trader.generate_fills_report()

        total_volume = 0.0
        buy_volume = 0.0
        sell_volume = 0.0
        total_fills_count = 0

        if not fills_raw.empty:
            fills_df = fills_raw[["last_px", "last_qty", "order_side"]].copy()
            fills_df["last_px"] = pd.to_numeric(fills_df["last_px"], errors="coerce")
            fills_df["last_qty"] = pd.to_numeric(fills_df["last_qty"], errors="coerce")
            fills_df["notional"] = fills_df["last_px"] * fills_df["last_qty"]

            total_fills_count = len(fills_df)
            total_volume = fills_df["notional"].sum()
            buy_volume = fills_df[fills_df["order_side"] == "BUY"]["notional"].sum()
            sell_volume = fills_df[fills_df["order_side"] == "SELL"]["notional"].sum()

            del fills_raw, fills_df

        print("\n" + "=" * 45)
        print(">>> Fill Statistics")
        print(f"Total fills       : {total_fills_count}")
        print(f"Total notional    : {total_volume:,.2f} USDT")
        print(f"  Buy             : {buy_volume:,.2f} USDT")
        print(f"  Sell            : {sell_volume:,.2f} USDT")
        print(f"Capital turnover  : {(total_volume / INITIAL_CAPITAL):>.2%}")
        print("=" * 45 + "\n")

    except Exception as e:
        print(f"Backtest failed: {e}")
        raise e
    finally:
        engine.dispose()


if __name__ == "__main__":
    run_backtest()
