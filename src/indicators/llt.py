# src/indicators/llt.py


class LLT:
    """
    Low-Lag Trendline (二阶低延迟趋势线).
    """

    def __init__(self, window: int):
        self.window = window
        self.alpha = 2.0 / (window + 1)

        # --- 预计算系数 ---
        a = self.alpha
        self.c_p0 = a - (a**2) / 4.0
        self.c_p1 = (a**2) / 2.0
        self.c_p2 = -(a - 0.75 * (a**2))
        self.c_l1 = 2 * (1 - a)
        self.c_l2 = -((1 - a) ** 2)

        # --- 状态变量 ---
        self.price_prev1: float | None = None
        self.price_prev2: float | None = None
        self.llt_prev1: float | None = None
        self.llt_prev2: float | None = None

        # 输出状态 (初始全部为 None)
        self.value: float | None = None
        self.slope: float | None = None
        self.initialized: bool = False

        # --- Warm-up Control ---
        self._warmup_countdown: int = window / 2

    def update(self, price: float) -> None:
        # 1. 过滤无效价格
        if price <= 0:
            return

        # 2. 计算逻辑

        # [Case 1] 第一根 Bar
        if self.price_prev1 is None:
            self.price_prev1 = price
            self.llt_prev1 = price

            # 第一根线只有数值，没有斜率
            self.value = price

        # [Case 2] 第二根 Bar
        elif self.price_prev2 is None:
            self.price_prev2 = self.price_prev1
            self.price_prev1 = price
            self.llt_prev2 = self.llt_prev1
            self.llt_prev1 = price

            # 此时 value 还是上一轮的 price
            self.slope = price - self.value
            self.value = price

        # [Case 3] 第三根及以后 (正常迭代)
        else:
            new_llt = (
                self.c_p0 * price
                + self.c_p1 * self.price_prev1
                + self.c_p2 * self.price_prev2
                + self.c_l1 * self.llt_prev1
                + self.c_l2 * self.llt_prev2
            )

            # 更新 slope (当前 LLT - 上一时刻 LLT)
            self.slope = new_llt - self.llt_prev1

            # 滚动状态
            self.price_prev2 = self.price_prev1
            self.price_prev1 = price
            self.llt_prev2 = self.llt_prev1
            self.llt_prev1 = new_llt
            self.value = new_llt

        # 3. 维护预热倒计时
        if not self.initialized:
            self._warmup_countdown -= 1
            if self._warmup_countdown <= 0:
                self.initialized = True

    @property
    def slope_direction(self) -> int:
        """
        1 (Up), -1 (Down), 0 (Flat or Unknown)
        """
        if self.slope is None:
            return 0

        if self.slope > 0:
            return 1
        elif self.slope < 0:
            return -1
        return 0
