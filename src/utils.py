import csv
import numpy as np
import gurobipy as gp
from pathlib import Path ; from time import perf_counter as timer


def suppress_gurobi_parallel_spam():
    (_ := gp.Model()).setParam("OutputFlag", 0)


def update_miscellaneous_csv(net_arbitrage_revenue, details, args):
    historical_or_forecasted = "historical" if args.is_historical else "forecasted"
    path_csv = Path(__file__).resolve().parents[1] / "data" / "outputs" / historical_or_forecasted / "net_arbitrage_revenues" / "miscellaneous.csv"

    with path_csv.open("r") as f:
        miscellaneous_index  = sum(1 for _ in f) - 1

    row_miscellaneous = [
        net_arbitrage_revenue,
        args.energy_capacity_rated,
        args.power_output_rated,
        args.state_of_health,
        args.state_of_charge_initial,
        args.state_of_charge_minimum,
        args.state_of_charge_maximum,
        args.self_discharge_rate,
        args.efficiency_charge,
        args.efficiency_discharge,
        args.rest_before_charge,
        args.rest_after_discharge,
        args.return_details,
        miscellaneous_index,
        args.date_start,
        args.date_end,
    ]
    
    with path_csv.open("a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row_miscellaneous)

    if args.return_details:
        np.save(path_csv.parents[1] / "details_miscellaneous" / f"{miscellaneous_index}.npy", details)


def update_monthly_csv(net_arbitrage_revenues_per_config, pairs_per_config, args):
    historical_or_forecasted = "historical" if args.is_historical else "forecasted"
    path_csv = Path(__file__).resolve().parents[1] / "data" / "outputs" / historical_or_forecasted / "net_arbitrage_revenues" / f"{args.month}.csv"

    with path_csv.open("a", newline="") as f:
        writer = csv.writer(f)

        for idx_config in range(len(pairs_per_config)):
            net_arbitrage_revenue = net_arbitrage_revenues_per_config[idx_config]
            energy_capacity_rated, power_output_rated = pairs_per_config[idx_config]

            writer.writerow([
                net_arbitrage_revenue,
                energy_capacity_rated,
                power_output_rated,
                args.state_of_health,
                args.state_of_charge_initial,
                args.state_of_charge_minimum,
                args.state_of_charge_maximum,
                args.self_discharge_rate,
                args.efficiency_charge,
                args.efficiency_discharge,
                args.rest_before_charge,
                args.rest_after_discharge,
            ])