import numpy as np


class Output:
    def __init__(
        self,
        num_periods,
        return_detail,
    ):
        #
        self.discharging_revenue: int = -1
        self.charging_cost: int = -1
        self.arbitrage_profit: int = -1
        #
        if return_detail:
            self.detail = np.full((5, num_periods), np.nan)