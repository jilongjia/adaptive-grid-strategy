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

# 导入配置
from backtest.adaptive_grid_binance.config import (
    BACKTEST_END,
    BACKTEST_START,
    INITIAL_CAPITAL,
    INSTRUMENT_SYMBOL,
    STRATEGY_CONFIG,
)

# 导入策略
from strategies.adaptive_grid import AdaptiveGridStrategy, AdaptiveGridStrategyConfig


def run_backtest():
    # ==========================================================================
    # 0. 基础设施配置
    # ==========================================================================
    CATALOG_PATH = "catalog"

    # 模拟环境设置
    FILL_PROBABILITY = 0.2
    FILL_SEED = 11
    LATENCY_NANOS = 10_000_000  # 10ms

    # 日志设置
    LOG_CONFIG = LoggingConfig(
        log_level="WARNING",
        log_level_file="INFO",
        log_directory="logs",
        log_file_name="binance_adaptive_grid_backtest",
        log_file_max_size=300_000_000,
        log_file_max_backup_count=100,
    )

    # ==========================================================================
    # 1. 加载数据与构建 Instrument ID (Setup)
    # ==========================================================================
    print("正在加载数据...")
    catalog = ParquetDataCatalog(CATALOG_PATH)

    VENUE = BINANCE
    instrument_id = InstrumentId.from_str(f"{INSTRUMENT_SYMBOL}.{VENUE}")

    instruments = catalog.instruments(instrument_ids=[instrument_id])
    if not instruments:
        raise ValueError(f"未在 Catalog 中找到 ID 为 {instrument_id} 的 Instrument。")
    instrument = instruments[0]

    # ==========================================================================
    # 2. 引擎配置 (Engine & Venue)
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

    # 配置 Venue
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
    # 3. 策略配置 (Strategy Configuration)
    # ==========================================================================
    print("正在配置策略参数...")

    strategy_config = AdaptiveGridStrategyConfig(
        instrument_id=instrument.id, **STRATEGY_CONFIG
    )

    strategy = AdaptiveGridStrategy(strategy_config)
    engine.add_strategy(strategy=strategy)

    # ==========================================================================
    # 4. 注册分析指标 (Register Analysis Statistics)
    # ==========================================================================
    print("正在注册分析指标...")

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
    # 5. 执行回测 (Run Backtest)
    # ==========================================================================
    try:
        print(f"启动回测引擎: {BACKTEST_START} 至 {BACKTEST_END} ...")
        engine.run(start=BACKTEST_START, end=BACKTEST_END)

        print("正在统计成交数据...")
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
        print(">>> 成交统计")
        print(f"总成交笔数: {total_fills_count}")
        print(f"总名义本金: {total_volume:,.2f} USDT")
        print(f"  - 买入: {buy_volume:,.2f} USDT")
        print(f"  - 卖出: {sell_volume:,.2f} USDT")
        print(f"资金周转率: {(total_volume / INITIAL_CAPITAL):>.2%}")
        print("=" * 45 + "\n")

        print("回测完成。")

    except Exception as e:
        print(f"回测过程中发生错误: {e}")
        raise e
    finally:
        engine.dispose()
        print("引擎资源清理完毕。")


if __name__ == "__main__":
    run_backtest()
