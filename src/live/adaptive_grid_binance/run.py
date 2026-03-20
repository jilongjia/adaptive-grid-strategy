# src/live/adaptive_grid_binance/run.py
import os

from dotenv import load_dotenv
from nautilus_trader.adapters.binance import (
    BINANCE,
    BinanceAccountType,
    BinanceDataClientConfig,
    BinanceExecClientConfig,
    BinanceLiveDataClientFactory,
    BinanceLiveExecClientFactory,
)
from nautilus_trader.config import (
    InstrumentProviderConfig,
    LoggingConfig,
    TradingNodeConfig,
)
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId, TraderId

from live.adaptive_grid_binance.config import (
    DEFAULT_STRATEGY_CONFIG,
    INSTRUMENT_CONFIGS,
)
from strategies.adaptive_grid import AdaptiveGridStrategy, AdaptiveGridStrategyConfig

# ==============================================================================
# 1. Global Setup
# ==============================================================================
load_dotenv()

VENUE = BINANCE
TRADER_ID = TraderId("ADAPTIVE-GRID-BOT-BINANCE")

BINANCE_API_KEY = os.getenv("BINANCE_MOMENTUM_RISK_PARITY_GRID_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_MOMENTUM_RISK_PARITY_GRID_API_SECRET")

# ==============================================================================
# 2. Instrument IDs & Leverage Map
# ==============================================================================
instrument_ids = []
futures_leverages = {}

for symbol, config in INSTRUMENT_CONFIGS.items():
    instrument_symbol = config["instrument_symbol"]
    instrument_id = InstrumentId.from_str(f"{instrument_symbol}.{VENUE}")
    instrument_ids.append(instrument_id)
    futures_leverages[symbol] = config["leverage"]

# ==============================================================================
# 3. Client & Node Configuration
# ==============================================================================
provider_config = InstrumentProviderConfig(load_ids=frozenset(instrument_ids))

data_client_config = BinanceDataClientConfig(
    api_key=BINANCE_API_KEY,
    api_secret=BINANCE_API_SECRET,
    account_type=BinanceAccountType.USDT_FUTURES,
    instrument_provider=provider_config,
)

exec_client_config = BinanceExecClientConfig(
    api_key=BINANCE_API_KEY,
    api_secret=BINANCE_API_SECRET,
    account_type=BinanceAccountType.USDT_FUTURES,
    instrument_provider=provider_config,
    use_reduce_only=True,
    futures_leverages=futures_leverages,
)

node_config = TradingNodeConfig(
    trader_id=TRADER_ID,
    logging=LoggingConfig(
        log_level="INFO",
        log_level_file="INFO",
        log_directory="logs",
        log_file_name="adaptive_grid_binance",
        log_file_max_size=100_000_000,
    ),
    data_clients={VENUE: data_client_config},
    exec_clients={VENUE: exec_client_config},
)

node = TradingNode(config=node_config)

node.add_data_client_factory(VENUE, BinanceLiveDataClientFactory)
node.add_exec_client_factory(VENUE, BinanceLiveExecClientFactory)

# ==============================================================================
# 4. Strategy Registration
# ==============================================================================
for symbol, config in INSTRUMENT_CONFIGS.items():
    instrument_symbol = config["instrument_symbol"]
    instrument_id = InstrumentId.from_str(f"{instrument_symbol}.{VENUE}")

    raw_strategy_config = DEFAULT_STRATEGY_CONFIG.copy()
    overrides = config.get("strategy_overrides", {})

    # Merge overrides into base config and inject instrument ID
    raw_strategy_config.update(overrides)
    raw_strategy_config["instrument_id"] = instrument_id

    strategy_config = AdaptiveGridStrategyConfig(**raw_strategy_config)
    strategy = AdaptiveGridStrategy(config=strategy_config)
    node.trader.add_strategy(strategy)

node.build()

# ==============================================================================
# 5. Entry Point
# ==============================================================================
if __name__ == "__main__":
    try:
        node.run()
    finally:
        node.dispose()
