import numpy as np
import gurobipy as gp

from .parameter import Parameter
from .output import Output


def optimize(
    parameter: Parameter,
    smp: np.ndarray,
    smp_ref: np.ndarray,
    return_detail: bool, 
):
    ecr = parameter.ecr                 # energy capacity rated
    por = parameter.por                 # power output rated
    soh = parameter.soh                 # state of health
    soc_ini = parameter.soc_ini         # state of charge initial
    soc_min = parameter.soc_min         # state of charge minimum
    soc_max = parameter.soc_max         # state of charge maximum
    sdr = parameter.sdr                 # self discharge rate
    ec = parameter.ec                   # efficiency charge
    ed = parameter.ed                   # efficiency discharge
    rbc = parameter.rbc                 # rest before charge
    rad = parameter.rad                 # rest after discharge
    eca = ecr * soh                     # energy capacity actual
    el_ini = eca * soc_ini              # energy level initial
    el_min = eca * soc_min              # energy level minimum
    el_max = eca * soc_max              # energy level maximum
    one_minus_sdr = 1 - sdr             # one minus self discharge rate
    one_over_ed = 1 / ed                # one over efficiency discharge
    num_periods = len(smp)              # number of periods in the given time horizon

    #
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    #
    dc = model.addVars(num_periods, vtype=gp.GRB.BINARY)
    dd = model.addVars(num_periods, vtype=gp.GRB.BINARY)
    poc = model.addVars(num_periods, lb=0, ub=por)
    pod = model.addVars(num_periods, lb=0, ub=por)
    el = model.addVars(num_periods, lb=el_min, ub=el_max)

    #
    model.addConstrs(
        dc[t] + dd[t]
        <=
        1
        for t in range(num_periods)
    )

    #
    model.addConstrs(
        poc[t]
        <=
        por * dc[t]
        for t in range(num_periods)
    )

    #
    model.addConstrs(
        pod[t]
        <=
        por * dd[t]
        for t in range(num_periods)
    )

    #
    model.addConstr(
        el[0]
        ==
        el_ini * one_minus_sdr
        + poc[0] * ec
        - pod[0] * one_over_ed
    )

    #
    model.addConstrs(
        el[t]
        ==
        el[t - 1] * one_minus_sdr
        + poc[t] * ec
        - pod[t] * one_over_ed
        for t in range(1, num_periods)
    )

    #
    if rbc != 0:
        model.addConstrs(
            (dc[t] - dc[t - 1]) * gp.quicksum(
                poc[tau] + pod[tau]
                for tau in range(t - rbc, t)
            )
            <=
            0
            for t in range(rbc, num_periods)
        )

    #
    if rad != 0:
        model.addConstrs(
            (dd[t] - dd[t + 1]) * gp.quicksum(
                poc[tau] + pod[tau]
                for tau in range(t + 1, t + 1 + rad)
            )
            <=
            0
            for t in range(num_periods - rad)
        )

    #
    discharging_revenue = gp.quicksum(
        smp[t] * pod[t]
        for t in range(num_periods)
    )

    #
    charging_cost = gp.quicksum(
        smp[t] * poc[t]
        for t in range(num_periods)
    )

    # 
    arbitrage_profit = discharging_revenue - charging_cost
    
    #
    model.setObjective(arbitrage_profit, gp.GRB.MAXIMIZE)

    #
    model.optimize()

    #
    if model.Status != gp.GRB.OPTIMAL:
        raise ValueError(model.Status)

    #
    output = Output(num_periods, return_detail)
    output.discharging_revenue = int(discharging_revenue.getValue())
    output.charging_cost = int(charging_cost.getValue())

    if smp_ref is not None:
        output.discharging_revenue = int((smp_ref * np.array(model.getAttr("X", pod).select())).sum())
        output.charging_cost = int((smp_ref * np.array(model.getAttr("X", poc).select())).sum())

    output.arbitrage_profit = output.discharging_revenue - output.charging_cost

    if return_detail:
        output.detail = np.array(model.getAttr("X")).reshape(5, num_periods)
        output.detail[-1] /= eca
    
    #
    return output