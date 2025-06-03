import numpy as np


class Output:
    def __init__(
        self,
        num_periods,
        return_detail,
    ):
        #
        self.bess_revenue_generation: int = -1
        self.plant_revenue_reduction: int = -1
        self.combined_revenue_net: int = -1
        #
        if return_detail:
            self.detail = np.full((5, num_periods), np.nan)