import os
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from time import perf_counter as timer
from concurrent.futures import ProcessPoolExecutor

from src.timeseries import get_smp
from src.solver import optimize
from src.utils import suppress_gurobi_parallel_spam


def arg_get():
    parser = argparse.ArgumentParser(description="RUN initialization.py and _pnnl.py FIRST; will do all monthly optimization; only depends whether its historical or forecasted smp")
    parser.add_argument("--is_historical", "--ih", action="store_true")
    global is_historical, historical_or_forecasted
    is_historical = parser.parse_args().is_historical
    historical_or_forecasted = "historical" if is_historical else "forecasted"

    if (not is_historical):
        raise NotImplementedError()


def get_all_months_smp(historical_or_forecasted: str):
    is_historical = True if historical_or_forecasted == "historical" else False
    timestamps = np.arange(np.datetime64("2024-01-01T00"), np.datetime64("2025-01-01T00"))
    timestamps_months = np.arange(timestamps[0].astype("datetime64[M]"), (timestamps[-1] + 1).astype("datetime64[M]"))
    global timestamps_months_str, system_marginal_prices_group_by_month, count_months
    timestamps_months_str = timestamps_months.astype(str).tolist()
    count_months = len(timestamps_months)

    system_marginal_prices_group_by_month = [
        get_smp(time_month_start, time_month_end, is_historical)
        for time_month_start, time_month_end in 
        zip(timestamps_months.astype("datetime64[h]"), (timestamps_months + 1) - np.timedelta64(1, "h"))
    ]


def job_per_processor(idx_month):
    system_marginal_price = system_marginal_prices_group_by_month[idx_month]

    return optimize(
        date_start=idx_month,
        date_end=idx_month,
        time_horizon_length=len(system_marginal_price),
        system_marginal_price=system_marginal_price,
        energy_capacity_rated=int(energy_capacity_rated),
        power_output_rated=int(power_output_rated),
        state_of_health=1,
        state_of_charge_initial=state_of_charge_minimum, ########### changed
        state_of_charge_minimum=state_of_charge_minimum,
        state_of_charge_maximum=state_of_charge_maximum,
        self_discharge_rate=0,
        efficiency_charge=efficiency,
        efficiency_discharge=efficiency,
        rest_before_charge=int(rest),
        rest_after_discharge=int(rest),
        return_details=False,
    )[0]


def inside_loops(technology: str, year: int, estimate: str, path_input, path_output, delta_efficiency: float):
    # for memory cleanness # for each csv input -> csv output with the same config order
    arr_params = pd.read_csv(path_input / f"{technology}_{year}_{estimate}.csv", header=0).to_numpy()

    net_arbitrage_revenues_all_configs_all_months = np.empty((arr_params.shape[0], count_months))
    for idx_config, vector_params in enumerate(arr_params):

        global energy_capacity_rated, power_output_rated, state_of_charge_minimum, state_of_charge_maximum, efficiency, rest
        energy_capacity_rated, power_output_rated, state_of_charge_minimum, state_of_charge_maximum, efficiency, rest, _, _ = vector_params.tolist()
        efficiency += delta_efficiency
        
        # PARALLE # spamming global for good
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            net_arbitrage_revenues_per_config_all_months = list(
                executor.map(job_per_processor, range(count_months))
            )

        net_arbitrage_revenues_all_configs_all_months[idx_config] = net_arbitrage_revenues_per_config_all_months

    pd.DataFrame(net_arbitrage_revenues_all_configs_all_months, columns=timestamps_months_str).to_csv(path_output / f"{technology}_{year}_{estimate}.csv", index=False)


def main():
    arg_get()
    get_all_months_smp(historical_or_forecasted)
    suppress_gurobi_parallel_spam()

    technology = "Lithium-ion_LFP"
    estimate = "Point"
    year = 2023

    arr_delta_efficiency = [-0.02, -0.01]
    path_input = Path(__file__).resolve().parents[0] / "data" / "inputs" / "pnnl"
    for delta_efficiency in arr_delta_efficiency:
        path_output = Path(__file__).resolve().parents[0] / "data" / "outputs" / "pnnl" / f"{delta_efficiency}"
        path_output.mkdir(parents=True, exist_ok=True)

        inside_loops(technology, year, estimate, path_input, path_output, delta_efficiency)


    # technology_all = ["Lithium-ion_LFP", "Lithium-ion_NMC", "Lead_Acid", "Vanadium_Redox_Flow", "Zinc"]
    # estimate_all = ["Point", "High", "Low"]
    # year_all = [2023, 2030]


    # for technology in technology_all:
    #     for year in year_all:

    #         if technology == "Zinc": # zinc is the only chemistry which parameters change with estimate type
    #             for estimate in estimate_all:
    #                 inside_loops(technology, year, estimate, path_input, path_output)
    #         else:
    #             inside_loops(technology, year, "Point", path_input, path_output)


if __name__=="__main__":
    main()