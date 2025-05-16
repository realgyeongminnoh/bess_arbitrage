import numpy as np
import gurobipy as gp


def solve(
    time_horizon_length: int,
    system_marginal_price: np.ndarray,
    power_output_rated: int,
    energy_capacity_rated: int,
    state_of_health: float,
    state_of_charge_initial: float,
    state_of_charge_minimum: float,
    state_of_charge_maximum: float,
    self_discharge_rate: float,
    efficiency_charge: float,
    efficiency_discharge: float,
    rest_before_charge: int,
    rest_after_discharge: int,
    return_details: bool,
):
    energy_capacity_actual = energy_capacity_rated * state_of_health
    energy_level_initial = energy_capacity_actual * state_of_charge_initial
    energy_level_minimum = energy_capacity_actual * state_of_charge_minimum
    energy_level_maximum = energy_capacity_actual * state_of_charge_maximum
    one_minus_self_discharge_rate = 1 - self_discharge_rate
    one_over_efficiency_discharge = 1 / efficiency_discharge

    model = gp.Model()
    model.setParam("OutputFlag", 0)

    decision_charge = model.addVars(time_horizon_length, vtype=gp.GRB.BINARY)
    decision_discharge = model.addVars(time_horizon_length, vtype=gp.GRB.BINARY)
    power_output_charge = model.addVars(time_horizon_length, lb=0, ub=power_output_rated)
    power_output_discharge = model.addVars(time_horizon_length, lb=0, ub=power_output_rated)
    energy_level = model.addVars(time_horizon_length, lb=energy_level_minimum, ub=energy_level_maximum)

    model.addConstrs(
        decision_charge[t] + decision_discharge[t] <= 1
        for t in range(time_horizon_length)
    )

    model.addConstrs(
        power_output_charge[t] <= power_output_rated * decision_charge[t]
        for t in range(time_horizon_length)
    )

    model.addConstrs(
        power_output_discharge[t] <= power_output_rated * decision_discharge[t]
        for t in range(time_horizon_length)
    )

    model.addConstr(
        energy_level[0] == energy_level_initial * one_minus_self_discharge_rate
        + power_output_charge[0] * efficiency_charge
        - power_output_discharge[0] * one_over_efficiency_discharge
    )

    model.addConstrs(
        energy_level[t] == energy_level[t-1] * one_minus_self_discharge_rate
        + power_output_charge[t] * efficiency_charge 
        - power_output_discharge[t] * one_over_efficiency_discharge
        for t in range(1, time_horizon_length)
    )

    if rest_before_charge != 0:
        model.addConstrs(
            (decision_charge[t] - decision_charge[t - 1])
            * gp.quicksum(
                (power_output_charge[tau] + power_output_discharge[tau])
                for tau in range(t - rest_before_charge, t)
            )
            <= 0
            for t in range(rest_before_charge, time_horizon_length)
        )

    if rest_after_discharge != 0:
        model.addConstrs(
            (decision_discharge[t] - decision_discharge[t + 1])
            * gp.quicksum(
                (power_output_charge[tau] + power_output_discharge[tau])
                for tau in range(t + 1, t + 1 + rest_after_discharge)
            )
            <= 0
            for t in range(time_horizon_length - rest_after_discharge)
        )

    model.setObjective(
        gp.quicksum(
            system_marginal_price[t] * (power_output_discharge[t] - power_output_charge[t])
            for t in range(time_horizon_length)
        ),
        gp.GRB.MAXIMIZE,
    )

    model.optimize()

    if model.Status == gp.GRB.OPTIMAL:
        if return_details:
            return model
        return model.ObjVal
    raise ValueError(
        "non-optimal solution\n"
        f"time_horizon_length: {time_horizon_length}\n"
        f"power_output_rated: {power_output_rated}\n"
        f"energy_capacity_rated: {energy_capacity_rated}\n"
        f"state_of_health: {state_of_health}\n"
        f"state_of_charge_initial: {state_of_charge_initial}\n"
        f"state_of_charge_minimum: {state_of_charge_minimum}\n"
        f"state_of_charge_maximum: {state_of_charge_maximum}\n"
        f"self_discharge_rate: {self_discharge_rate}\n"
        f"efficiency_charge: {efficiency_charge}\n"
        f"efficiency_discharge: {efficiency_discharge}\n"
        f"rest_before_charge: {rest_before_charge}\n"
        f"rest_after_discharge: {rest_after_discharge}\n"
        f"return_details: {return_details}\n"
    )