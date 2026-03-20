# src/strategy/adaptive_grid.py

import secrets
from dataclasses import dataclass
from datetime import timedelta

from nautilus_trader.common.events import TimeEvent
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.enums import (
    AggregationSource,
    BarAggregation,
    OrderSide,
    PriceType,
    TimeInForce,
)
from nautilus_trader.model.events import OrderCanceled, OrderFilled, OrderRejected
from nautilus_trader.model.identifiers import ClientOrderId, InstrumentId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders import LimitOrder
from nautilus_trader.trading.strategy import Strategy

from indicators import LLT, RSI, Volatility

# ==============================================================================
# Data Structures
# ==============================================================================


@dataclass(frozen=True)
class GridTarget:
    price: Price
    quantity: Quantity


@dataclass
class GridLevel:
    side: OrderSide
    current_order: LimitOrder | None = None
    target: GridTarget | None = None

    @property
    def is_inflight(self) -> bool:
        return self.current_order is not None and self.current_order.is_inflight

    @property
    def is_booked(self) -> bool:
        return (
            self.current_order is not None
            and self.current_order.is_open
            and not self.current_order.is_inflight
        )

    def update_target(self, new_target: GridTarget | None) -> None:
        self.target = new_target

    def should_update(self, threshold_bps: float, tick_size: float) -> bool:
        if not self.target or not self.is_booked:
            return False

        current_px = float(self.current_order.price)
        target_px = float(self.target.price)

        if abs(target_px - current_px) < 1e-9:
            return False

        threshold_value = current_px * (threshold_bps / 10000.0)
        effective_threshold = max(threshold_value, tick_size)

        return abs(target_px - current_px) > effective_threshold


# ==============================================================================
# Strategy Configuration
# ==============================================================================


class AdaptiveGridStrategyConfig(StrategyConfig, frozen=True):
    """
    Configuration for Adaptive Grid Strategy.
    """

    instrument_id: InstrumentId

    # ----------------------------------------------------------------
    # 1. Basic Trading Parameters
    # ----------------------------------------------------------------
    order_quantity: float = 100.0

    target_position: float = 0.0
    max_position: float = 1000.0
    min_position: float = -1000.0

    # ----------------------------------------------------------------
    # 2. Grid Pricing Logic (Alpha)
    # ----------------------------------------------------------------
    # Skew Logic
    inventory_skew_factor: float = 0.5
    trend_skew_factor: float = 0.5
    reversal_skew_factor: float = 0.5

    # Spread Calculation
    base_half_spread_bps: float = 5.0
    vol_half_spread_factor: float = 5.0

    # ----------------------------------------------------------------
    # 3. Indicators & Signal Parameters
    # ----------------------------------------------------------------
    volatility_smoothing_factor: float = 0.01

    # Trend (LLT)
    trend_llt_windows: tuple[int, ...] = tuple(range(5, 720 + 1, 3))

    # Reversal (LLT + RSI)
    reversal_llt_windows: tuple[int, ...] = tuple(range(1, 10 + 1, 1))
    rsi_llt_window: int = 30
    rsi_windows: tuple[int, ...] = (9, 14, 21)
    rsi_lookback_window: int = 10
    rsi_oversold_threshold: float = 20.0
    rsi_overbought_threshold: float = 80.0

    # ----------------------------------------------------------------
    # 4. Anchor Management
    # ----------------------------------------------------------------
    anchor_decay_factor: float = 0.01

    # ----------------------------------------------------------------
    # 5. Execution & Timer Intervals
    # ----------------------------------------------------------------
    volatility_sample_interval_sec: float = 1.0
    grid_target_update_interval_sec: float = 1.0
    grid_update_threshold_bps: float = 1.0


# ==============================================================================
# Strategy Implementation
# ==============================================================================


class AdaptiveGridStrategy(Strategy):
    """
    Adaptive Grid Strategy.
    """

    TIMER_VOLATILITY_UPDATE = "01_volatility_update"
    TIMER_GRID_TARGET_UPDATE = "02_grid_target_update"

    def __init__(self, config: AdaptiveGridStrategyConfig) -> None:
        super().__init__(config)
        self.instrument_id = config.instrument_id

        # --- Indicators ---
        self.volatility = Volatility(alpha=config.volatility_smoothing_factor)
        self.trend_llts: list[LLT] = [LLT(window=w) for w in config.trend_llt_windows]
        self.reversal_llts: list[LLT] = [
            LLT(window=w) for w in config.reversal_llt_windows
        ]
        self.rsi_llt = LLT(window=config.rsi_llt_window)
        self.rsis: list[RSI] = [
            RSI(window=w, lookback_window=config.rsi_lookback_window)
            for w in config.rsi_windows
        ]

        # --- State Variables ---
        self.anchor_px: float | None = None
        self.inventory_ratio: float = 0.0
        self.trend_strength: float = 0.0
        self.reversal_strength: float = 0.0

        # --- Order Containers ---
        self.bid_level = GridLevel(side=OrderSide.BUY)
        self.ask_level = GridLevel(side=OrderSide.SELL)

    # ==========================================================================
    # Lifecycle Methods
    # ==========================================================================

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.instrument_id)
        if not self.instrument:
            self.log.error(f"Could not find instrument: {self.instrument_id}")
            self.stop()
            return

        self._update_inventory_ratio()

        # 1. Subscriptions
        bar_spec = BarSpecification(
            step=1,
            aggregation=BarAggregation.MINUTE,
            price_type=PriceType.LAST,
        )
        bar_type = BarType(
            instrument_id=self.instrument_id,
            bar_spec=bar_spec,
            aggregation_source=AggregationSource.EXTERNAL,
        )

        self.subscribe_bars(bar_type)
        self.subscribe_quote_ticks(self.instrument_id)

        # 2. Warmup
        trend_req = max(self.config.trend_llt_windows)
        rev_req = max(self.config.reversal_llt_windows)
        rsi_req = (
            self.config.rsi_llt_window
            + max(self.config.rsi_windows)
            + self.config.rsi_lookback_window
        )
        warmup_needed = max(trend_req, rev_req, rsi_req)
        start_time = self.clock.utc_now() - timedelta(minutes=warmup_needed + 720)
        self.request_bars(bar_type=bar_type, start=start_time)

        # 3. Timers
        self.clock.set_timer(
            name=self.TIMER_VOLATILITY_UPDATE,
            interval=timedelta(seconds=self.config.volatility_sample_interval_sec),
            callback=self.on_volatility_update_timer,
            fire_immediately=True,
        )
        self.clock.set_timer(
            name=self.TIMER_GRID_TARGET_UPDATE,
            interval=timedelta(seconds=self.config.grid_target_update_interval_sec),
            callback=self.on_grid_target_update_timer,
            fire_immediately=True,
        )

    def on_stop(self) -> None:
        self.cancel_all_orders(self.instrument_id)
        self.close_all_positions(instrument_id=self.instrument_id, reduce_only=True)

    # ==========================================================================
    # Event Handlers: Data & Timers
    # ==========================================================================

    def on_historical_data(self, data: Data) -> None:
        if isinstance(data, Bar):
            self._update_indicators(float(data.close))

    def on_bar(self, bar: Bar) -> None:
        self._update_indicators(float(bar.close))

    def on_volatility_update_timer(self, event: TimeEvent) -> None:
        quote = self.cache.quote_tick(self.instrument_id)
        if quote is None:
            return

        best_bid_px = float(quote.bid_price)
        best_ask_px = float(quote.ask_price)
        current_mid_px = (best_bid_px + best_ask_px) / 2.0

        self.volatility.update(current_mid_px)

    def on_grid_target_update_timer(self, event: TimeEvent) -> None:
        # 1. Check indicators
        if not self._check_indicators_ready():
            return
        # 2. Update Targets
        self._update_grid_targets()
        # 3. Reconcile Orders
        self._reconcile_grid_orders()

    # ==========================================================================
    # Event Handlers: Orders
    # ==========================================================================

    def on_order_filled(self, event: OrderFilled) -> None:
        if self.cache.is_order_closed(event.client_order_id):
            order = self.cache.order(event.client_order_id)
            is_grid_order = order and "GRID" in (order.tags or [])

            # Hard Reset Anchor on Fill
            if is_grid_order:
                fill_px = float(event.last_px)
                old_anchor = self.anchor_px
                self.anchor_px = fill_px

                self.log.info(
                    f"⚓ Order Filled! Hard Reset Anchor: {old_anchor} -> {self.anchor_px}"
                )
                self._remove_order_ref(event.client_order_id)

            self._update_inventory_ratio()
            self._update_grid_targets()
            self._reconcile_grid_orders()

    def on_order_canceled(self, event: OrderCanceled) -> None:
        self._remove_order_ref(event.client_order_id)

    def on_order_rejected(self, event: OrderRejected) -> None:
        self._remove_order_ref(event.client_order_id)

    # ==========================================================================
    # Logic: Signals & Indicators
    # ==========================================================================

    def _update_indicators(self, px: float) -> None:
        for llt in self.trend_llts:
            llt.update(px)
        self._update_trend_strength()

        for llt in self.reversal_llts:
            llt.update(px)

        self.rsi_llt.update(px)
        if self.rsi_llt.initialized:
            smoothed = self.rsi_llt.value
            for rsi in self.rsis:
                rsi.update(smoothed)
        self._update_reversal_strength()

        # # 4. Logging
        # trend_slopes = [int(llt.slope_direction) for llt in self.trend_llts]
        # rev_slopes = [int(llt.slope_direction) for llt in self.reversal_llts]
        # rsi_values = [
        #     f"{rsi.value:.1f}" if rsi.value is not None else "-" for rsi in self.rsis
        # ]

        # self.log.info(
        #     f"\nINDICATORS UPDATE | Price: {px:.6f}\n"
        #     f"  > Trend LLT (Slope) : {trend_slopes}\n"
        #     f"  > Rev LLT (Slope)   : {rev_slopes}\n"
        #     f"  > RSI (Values)      : {rsi_values} (SmoothLLT: {self.rsi_llt.value:.6f})"
        # )

    def _update_trend_strength(self) -> None:
        if not all(llt.initialized for llt in self.trend_llts):
            self.trend_strength = 0.0
            return
        score = sum(llt.slope_direction for llt in self.trend_llts)
        self.trend_strength = score / len(self.trend_llts)

    def _update_reversal_strength(self) -> None:
        if not (
            all(llt.initialized for llt in self.reversal_llts)
            and all(rsi.initialized for rsi in self.rsis)
        ):
            self.reversal_strength = 0.0
            return

        is_trend_up = all(llt.slope_direction == 1 for llt in self.reversal_llts)
        is_trend_down = all(llt.slope_direction == -1 for llt in self.reversal_llts)

        score = 0.0
        if is_trend_up:
            for rsi in self.rsis:
                if rsi.min_in_lookback < self.config.rsi_oversold_threshold:
                    score += 1.0
        elif is_trend_down:
            for rsi in self.rsis:
                if rsi.max_in_lookback > self.config.rsi_overbought_threshold:
                    score -= 1.0

        self.reversal_strength = score / len(self.rsis) if self.rsis else 0.0

    def _check_indicators_ready(self) -> bool:
        if not self.volatility.initialized:
            return False
        if not all(llt.initialized for llt in self.trend_llts):
            return False
        if not all(llt.initialized for llt in self.reversal_llts):
            return False
        if not self.rsi_llt.initialized:
            return False
        if not all(rsi.initialized for rsi in self.rsis):
            return False
        return True

    # ==========================================================================
    # Logic: State & Pricing
    # ==========================================================================

    def _update_inventory_ratio(self) -> None:
        current_pos = float(self.portfolio.net_position(self.instrument_id))
        target_pos = self.config.target_position
        max_pos = self.config.max_position
        min_pos = self.config.min_position

        if abs(current_pos - target_pos) < 1e-9:
            self.inventory_ratio = 0.0
        elif current_pos > target_pos:
            denom = max_pos - target_pos
            self.inventory_ratio = (
                (current_pos - target_pos) / denom if denom > 0 else 1.0
            )
        else:
            denom = target_pos - min_pos
            self.inventory_ratio = (
                (current_pos - target_pos) / denom if denom > 0 else -1.0
            )

        # Clamp strictly between -1.0 and 1.0
        self.inventory_ratio = max(-1.0, min(1.0, self.inventory_ratio))

    def _apply_anchor_decay(self, current_mid_px: float) -> None:
        """
        Soft Update: EMA Decay towards market price.
        """
        if self.anchor_px is None:
            self.anchor_px = current_mid_px
            self.log.info(f"⚓ Initialized Anchor to Mid: {self.anchor_px:.6f}")
            return

        alpha = self.config.anchor_decay_factor
        old_anchor = self.anchor_px

        new_anchor = (old_anchor * (1 - alpha)) + (current_mid_px * alpha)
        self.anchor_px = new_anchor

    def _update_grid_targets(self) -> None:
        quote = self.cache.quote_tick(self.instrument_id)
        if quote is None:
            return

        best_bid_px = float(quote.bid_price)
        best_ask_px = float(quote.ask_price)
        current_mid_px = (best_bid_px + best_ask_px) / 2.0

        # 1. Apply Anchor Decay
        self._apply_anchor_decay(current_mid_px)

        anchor_px = self.anchor_px
        if anchor_px is None:
            return

        vol = self.volatility.value
        tick_size = float(self.instrument.price_increment)

        # ----------------------------------------------------------------------
        # 1. Calculate Reservation Price (Alpha Only)
        # ----------------------------------------------------------------------
        trend_skew = (
            anchor_px * vol * self.trend_strength * self.config.trend_skew_factor
        )
        reversal_skew = (
            anchor_px * vol * self.reversal_strength * self.config.reversal_skew_factor
        )

        total_skew = trend_skew + reversal_skew
        reservation_px = anchor_px + total_skew

        # ----------------------------------------------------------------------
        # 2. Calculate Base Spreads
        # ----------------------------------------------------------------------
        base_half_spread = anchor_px * (self.config.base_half_spread_bps / 10000.0)
        vol_half_spread = anchor_px * vol * self.config.vol_half_spread_factor
        total_half_spread = base_half_spread + vol_half_spread

        raw_bid_px = reservation_px - total_half_spread
        raw_ask_px = reservation_px + total_half_spread

        # ----------------------------------------------------------------------
        # 3. Constraints Phase 1 & 2 & 3 (Anchor, Market, De-cross)
        # ----------------------------------------------------------------------
        # Anchor Bounds
        raw_bid_px = min(raw_bid_px, anchor_px - tick_size)
        raw_ask_px = max(raw_ask_px, anchor_px + tick_size)

        # Market Limits (Post-Only Safety)
        raw_bid_px = min(raw_bid_px, best_ask_px - tick_size)
        raw_ask_px = max(raw_ask_px, best_bid_px + tick_size)

        # Internal De-Cross
        if raw_bid_px >= raw_ask_px:
            mid = (raw_bid_px + raw_ask_px) / 2.0
            raw_bid_px = mid - tick_size
            raw_ask_px = mid + tick_size

        # ----------------------------------------------------------------------
        # 4. Apply Inventory Offset (Final Penalty)
        # ----------------------------------------------------------------------
        inventory_skew_offset = (
            anchor_px
            * vol
            * abs(self.inventory_ratio)
            * self.config.inventory_skew_factor
        )

        if self.inventory_ratio > 0:
            raw_bid_px -= inventory_skew_offset
        elif self.inventory_ratio < 0:
            raw_ask_px += inventory_skew_offset

        # ----------------------------------------------------------------------
        # 5. Set Targets
        # ----------------------------------------------------------------------
        quantity = self.instrument.make_qty(self.config.order_quantity)

        if self.inventory_ratio < 1.0:
            bid_price = self.instrument.make_price(raw_bid_px)
            self.bid_level.update_target(GridTarget(bid_price, quantity))
        else:
            self.bid_level.update_target(None)

        if self.inventory_ratio > -1.0:
            ask_price = self.instrument.make_price(raw_ask_px)
            self.ask_level.update_target(GridTarget(ask_price, quantity))
        else:
            self.ask_level.update_target(None)

        # ----------------------------------------------------------------------
        # 6. Logging (Restored to Original Format)
        # ----------------------------------------------------------------------
        def format_price(price: Price | None) -> str:
            return f"{float(price):.6f}" if price else "-"

        current_bid_price = (
            self.bid_level.current_order.price if self.bid_level.current_order else None
        )
        current_ask_price = (
            self.ask_level.current_order.price if self.ask_level.current_order else None
        )

        target_bid_price = (
            self.bid_level.target.price if self.bid_level.target else None
        )
        target_ask_price = (
            self.ask_level.target.price if self.ask_level.target else None
        )

        grid_header = f"{'Bid (Current)':<12} | {'Bid (Target)':<12} || {'Ask (Current)':<12} | {'Ask (Target)':<12}"
        grid_row = (
            f"{format_price(current_bid_price):<12} | {format_price(target_bid_price):<12} || "
            f"{format_price(current_ask_price):<12} | {format_price(target_ask_price):<12}"
        )

        self.log.info(
            f"\nPRICING: Anchor={anchor_px:.6f} | ResPrice={reservation_px:.6f}\n"
            f"  > Inventory: Current={self.portfolio.net_position(self.instrument_id)} Target={self.config.target_position} Ratio={self.inventory_ratio:.2f}\n"
            f"  > Skew     : Inventory={inventory_skew_offset:.6f} Trend={trend_skew:.6f} Reversal={reversal_skew:.6f} => Total={total_skew:.6f}\n"
            f"  > Spread   : Base={base_half_spread:.6f} Vol={vol_half_spread:.6f} => Total={total_half_spread:.6f}\n"
            f"  > GRID STATUS:\n"
            f"    {grid_header}\n"
            f"    {grid_row}"
        )

    # ==========================================================================
    # Logic: Execution
    # ==========================================================================

    def _reconcile_grid_orders(self) -> None:
        threshold = self.config.grid_update_threshold_bps
        tick_size = float(self.instrument.price_increment)

        for level in [self.bid_level, self.ask_level]:
            if level.target is None:
                if level.is_booked:
                    self.cancel_order(level.current_order)
                continue

            if not level.is_booked and not level.is_inflight:
                client_order_id = ClientOrderId(f"GRID-{secrets.token_hex(6)}")

                new_order = self.order_factory.limit(
                    client_order_id=client_order_id,
                    instrument_id=self.instrument_id,
                    order_side=level.side,
                    quantity=level.target.quantity,
                    price=level.target.price,
                    time_in_force=TimeInForce.GTC,
                    post_only=True,
                    tags=["GRID"],
                )
                self.submit_order(new_order)
                level.current_order = new_order
                continue

            if level.should_update(threshold, tick_size):
                self.modify_order(
                    order=level.current_order,
                    price=level.target.price,
                )

    def _remove_order_ref(self, order_id: ClientOrderId) -> None:
        for level in [self.bid_level, self.ask_level]:
            if level.current_order and level.current_order.client_order_id == order_id:
                level.current_order = None
                return
