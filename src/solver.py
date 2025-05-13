import gurobipy as gp

from src.utils import string_for_non_optimality
from src.timeseries import Timeseries
from src.parameter import Parameter


class Solver:
    def __init__(
            self, 
            timeseries: Timeseries, 
            parameter: Parameter, 
            idx_config: int, 
            do_efficiency: bool = True,
            do_rest: bool = True,
            return_model: bool = False,
    ):

        self.timeseries = timeseries
        self.parameter = parameter
        self.idx_config = idx_config
        self.do_efficiency = do_efficiency
        self.do_rest = do_rest
        self.return_model = return_model

        if not self.do_efficiency:
            self.parameter.efficiencies[self.idx_config] = 1


    def solve(self):
        # parameters localization
        smp = self.timeseries.smp
        time_count = self.timeseries.minute_count if self.timeseries.is_minute else self.timeseries.hour_count
        capacity = self.parameter.capacities[self.idx_config]
        power = self.parameter.powers[self.idx_config]
        efficiency = self.parameter.efficiencies[self.idx_config]
        rest_before_charge = self.parameter.rests_before_charge[self.idx_config]
        rest_after_discharge = self.parameter.rests_after_discharge[self.idx_config]

        # model declaration
        model = gp.Model()
        model.setParam("OutputFlag", 0)

        # variables declaration
        soc = model.addVars(time_count + 1, lb=0, ub=capacity, name="s")
        charge = model.addVars(time_count, lb=0, ub=power, name="c")
        discharge = model.addVars(time_count, lb=0, ub=power, name="d")
        switch_charge = model.addVars(time_count, vtype=gp.GRB.BINARY, name="uc")
        switch_discharge = model.addVars(time_count, vtype=gp.GRB.BINARY, name="ud")

        # constraints declaration
        model.addConstrs(   # charge true upper bound
            charge[t] <= power * switch_charge[t]
            for t in range(time_count)
        )
        model.addConstrs(   # discharge true upper bound
            discharge[t] <= power * switch_discharge[t]
            for t in range(time_count)
        )
        model.addConstrs(    # SoC initial and final value
            soc[t] == 0
            for t in (0, time_count)
        )
        model.addConstrs(   # SoC dynamics
            soc[t+1] == soc[t] + charge[t] * efficiency - discharge[t] / efficiency
            for t in range(time_count)
        )
        model.addConstrs(   # no simultaneous charging and discharging
            switch_charge[t] + switch_discharge[t] <= 1
            for t in range(time_count)
        )
        if self.do_rest:
            if rest_before_charge != 0:
                model.addConstrs(   # BESS must be idle during the immediate preceding RBC intervals before charging BEGINS AT interval t
                    gp.quicksum((charge[tau] + discharge[tau]) for tau in range(t-rest_before_charge, t)) *
                    (switch_charge[t] - switch_charge[t-1]) <= 0
                    for t in range(rest_before_charge, time_count)
                )
            if rest_after_discharge != 0:
                model.addConstrs(   # BESS must be idle during the immediate following RAC intervals after discharging STOPS BEFORE interval t+1
                    gp.quicksum((charge[tau] + discharge[tau]) for tau in range(t+1, t+rest_after_discharge+1)) *
                    (switch_discharge[t] - switch_discharge[t+1]) <= 0
                    for t in range(time_count-rest_after_discharge)
                )

        # objective declaration
        discharge_revenue = gp.quicksum(smp[t] * discharge[t] for t in range(time_count))
        charge_opportunity_cost = gp.quicksum(smp[t] * charge[t] for t in range(time_count))
        net_arbitrage_revenue = discharge_revenue - charge_opportunity_cost
        model.setObjective(net_arbitrage_revenue, gp.GRB.MAXIMIZE)

        # optimization call
        model.optimize()

        # result
        if model.Status == gp.GRB.OPTIMAL:
            if self.return_model:
                return model
            return model.ObjVal # net_arbitrage_revenue
        else:
            raise ValueError(string_for_non_optimality(self))


    def money(self):
        capex = self.parameter.capexes[self.idx_config]
        opex = self.parameter.opexes[self.idx_config]
    
 