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

# ==========================
# 1. 全局设置
# ==========================
# 加载环境变量
load_dotenv()

VENUE = BINANCE
TRADER_ID = TraderId("ADAPTIVE-GRID-BOT-BINANCE")

BINANCE_API_KEY = os.getenv("BINANCE_MOMENTUM_RISK_PARITY_GRID_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_MOMENTUM_RISK_PARITY_GRID_API_SECRET")

# ==============================================================================
# 2. 准备 Instrument ID 和 杠杆字典
# ==============================================================================
# 收集所有的 Instrument ID
instrument_ids = []
futures_leverages = {}

for symbol, config in INSTRUMENT_CONFIGS.items():
    instrument_symbol = config["instrument_symbol"]

    # 创建 InstrumentId
    instrument_id = InstrumentId.from_str(f"{instrument_symbol}.{VENUE}")
    instrument_ids.append(instrument_id)

    # 这里的 symbol 就是 key (例如 ETHUSDT)，用于映射杠杆
    futures_leverages[symbol] = config["leverage"]

print(f"准备交易的 Instrument IDs: {instrument_ids}")
print(f"杠杆配置: {futures_leverages}")

# ==============================================================================
# 3. 客户端与节点配置
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
# 4. 批量实例化并注册策略
# ==============================================================================

# 修改点：循环变量更新
for symbol, config in INSTRUMENT_CONFIGS.items():
    instrument_symbol = config["instrument_symbol"]
    instrument_id = InstrumentId.from_str(f"{instrument_symbol}.{VENUE}")

    raw_strategy_config = DEFAULT_STRATEGY_CONFIG.copy()

    overrides = config.get("strategy_overrides", {})

    # 合并参数
    raw_strategy_config.update(overrides)

    # 强制注入 Instrument ID
    raw_strategy_config["instrument_id"] = instrument_id

    # 实例化配置对象 (Pydantic Model)
    strategy_config = AdaptiveGridStrategyConfig(**raw_strategy_config)

    # 实例化策略
    strategy = AdaptiveGridStrategy(config=strategy_config)

    # 添加到节点
    node.trader.add_strategy(strategy)

    # 打印确认信息 (从合并后的字典中读取 quantity，确保准确)
    print(f"已注册策略: {instrument_id} (Qty: {raw_strategy_config['order_quantity']})")

# 系统初始化
node.build()

# ==============================================================================
# 5. 运行
# ==============================================================================
if __name__ == "__main__":
    try:
        print("启动自适应网格策略...")
        node.run()
    finally:
        node.dispose()
