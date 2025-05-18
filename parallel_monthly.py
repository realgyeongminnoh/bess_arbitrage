import os
import argparse
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from src.timeseries import get_datetime64, get_smp
from src.solver import optimize
from src.utils import suppress_gurobi_parallel_spam, update_monthly_csv


def parse_args():
    parser = argparse.ArgumentParser(description="parallelized for these two: rated energy capacity and power output")
    # TIME-RELATED ARGS
    parser.add_argument("--is_historical", "--ih", action="store_true")
    parser.add_argument("--month", "--m", type=int, required=True, help="yyyymm; ex) 2022.01.01 ~ 31 -> \"--fms 202201\"")
    # OTHER RANGED ARGS
    parser.add_argument("--energy_capacity_rated_start", "--ecrs", type=int, required=False, default=1000, help="start of the range of energy capacity rated; kWh; default = 1000")
    parser.add_argument("--energy_capacity_rated_increment", "--ecri", type=int, required=False, default=1000, help="increment of the range of energy capacity rated; kWh; default = 1000")
    parser.add_argument("--energy_capacity_rated_end", "--ecre", type=int, required=False, default=100000, help="end of the range of energy capacity rated; kWh; default = 100000")
    parser.add_argument("--power_output_rated_start", "--pors", type=int, required=False, default=1000, help="start of the range of power output rated; kW; default = 1000")
    parser.add_argument("--power_output_rated_increment", "--pori", type=int, required=False, default=1000, help="increment of the range of power output rated; kW; default = 1000")
    parser.add_argument("--power_output_rated_end", "--pore", type=int, required=False, default=100000, help="end of the range of power output rated; kW; default = 100000")
    # OTHER ARGS
    parser.add_argument("--state_of_health", "--soh", type=float, required=False, default=1, help="state of health; pu; fixed")
    parser.add_argument("--state_of_charge_initial", "--socini", type=float, required=False, default=0, help="state of charge initial; pu")
    parser.add_argument("--state_of_charge_minimum", "--socmin", type=float, required=False, default=0, help="state of charge minimum; pu")
    parser.add_argument("--state_of_charge_maximum", "--socmax", type=float, required=False, default=1, help="state of charge maximum; pu")
    parser.add_argument("--self_discharge_rate", "--sdr", type=float, required=False, default=0, help="self-discharge rate; pu")
    parser.add_argument("--efficiency_charge", "--ec", type=float, required=False, default=1, help="efficiency charge; pu")
    parser.add_argument("--efficiency_discharge", "--ed", type=float, required=False, default=1, help="efficiency discharge; pu")
    parser.add_argument("--rest_before_charge", "--rbc", type=int, required=False, default=0, help="rest before charge; h; int")
    parser.add_argument("--rest_after_discharge", "--rad", type=int, required=False, default=0, help="rest after discharge; h; int")
    return parser.parse_args()


def validate_args(args):
    # TIME-RELATED ARGS
    if (not args.is_historical):
        raise NotImplementedError()
        
    historical_or_forecasted = "historical" if args.is_historical else "forecasted"    
    timestamps = np.load(Path(__file__).resolve().parents[0] / "data" / "inputs" / historical_or_forecasted / "timestamps.npy")
    full_month_start = int(str(timestamps[0])[:7].replace("-", ""))
    full_month_end_enddate_excluded = int(str(timestamps[-1])[:7].replace("-", ""))

    if not (full_month_start <= args.month):
        raise ValueError(f"full_month_start from initialization (timestamps) = {full_month_start} <= {args.month} = month")
    if not (args.month <= full_month_end_enddate_excluded):
        raise ValueError(f"month = {args.month} <= {full_month_end_enddate_excluded} = full_month_end (enddate excluded) from initialization (timestamps)")
    
    # OTHER RANGED ARGS
    if not (0 < args.energy_capacity_rated_start * args.energy_capacity_rated_increment * args.energy_capacity_rated_end):
        raise ValueError("non zero energy capacity rated-related inputs")
    if not (0 < args.power_output_rated_start * args.power_output_rated_increment * args.power_output_rated_end):
        raise ValueError("non zero power output rated-related inputs")
    if not (0 <= args.energy_capacity_rated_end - args.energy_capacity_rated_start):
        raise ValueError("range end should be equal to or greater than range start")
    if not (0 <= args.power_output_rated_end - args.power_output_rated_start):
        raise ValueError("range end should be equal to or greater than range start")
    if not (0 < args.energy_capacity_rated_increment):
        raise ValueError("increment cannot be zero; just put nonzero number and start = end to run with fixed energy capacity rated (but ranged power output rated)")    
    if not (0 < args.power_output_rated_increment):
        raise ValueError("increment cannot be zero; just put nonzero number and start = end to run with fixed power output rated (but ranged energy capacity rated)")

    # OTHER FIXED ARGS
    if not (0 < args.state_of_health <= 1):
        raise ValueError("state_of_health")
    if not (0 <= args.state_of_charge_initial <= 1):
        raise ValueError("state_of_charge_initial")
    if not (0 <= args.state_of_charge_minimum < 1):
        raise ValueError("state_of_charge_minimum")
    if not (0 < args.state_of_charge_maximum <= 1):
        raise ValueError("state_of_charge_maximum")
    if not (0 <= args.self_discharge_rate < 1):
        raise ValueError("self_discharge_rate")
    if not (0 < args.efficiency_charge <= 1):
        raise ValueError("efficiency_charge")
    if not (0 < args.efficiency_discharge <= 1):
        raise ValueError("efficiency_discharge")
    if not (0 <= args.rest_before_charge):
        raise ValueError("rest_before_charge")
    if not (0 <= args.rest_after_discharge):
        raise ValueError("rest_after_discharge")


def job_per_processor(idx_config):
    energy_capacity_rated, power_output_rated = pairs_per_config[idx_config]

    net_arbitrage_revenue, _ = optimize(
        date_start=date_start,
        date_end=date_end,
        time_horizon_length=time_horizon_length,
        system_marginal_price=system_marginal_price,
        energy_capacity_rated=energy_capacity_rated,
        power_output_rated=power_output_rated,
        state_of_health=state_of_health,
        state_of_charge_initial=state_of_charge_initial,
        state_of_charge_minimum=state_of_charge_minimum,
        state_of_charge_maximum=state_of_charge_maximum,
        self_discharge_rate=self_discharge_rate,
        efficiency_charge=efficiency_charge,
        efficiency_discharge=efficiency_discharge,
        rest_before_charge=rest_before_charge,
        rest_after_discharge=rest_after_discharge,
        return_details=False,
    )

    return net_arbitrage_revenue


def main():
    args = parse_args()
    validate_args(args)

    # TIME-RELATED ARGS
    global date_start, date_end, time_horizon_length, system_marginal_price
    time_start = get_datetime64(args.month * 100 + 1, False)
    time_end = np.datetime64(time_start.astype("datetime64[M]") + 1, "h") - np.timedelta64(1, "h")
    date_start = str(time_start.astype("datetime64[D]")).replace("-", "")
    date_end = str(np.datetime64(time_end.astype("datetime64[D]") + 1, "h").astype("datetime64[D]")).replace("-", "")
    time_horizon_length = int((time_end - time_start + 1).astype(int))    
    system_marginal_price = get_smp(time_start, time_end, args.is_historical)

    # OTHER RANGED ARGS
    global pairs_per_config
    pairs_per_config = [
        (energy_capacity_rated, power_output_rated)
        for energy_capacity_rated in range(
            args.energy_capacity_rated_start, 
            args.energy_capacity_rated_end + args.energy_capacity_rated_increment, 
            args.energy_capacity_rated_increment
        ) 
        for power_output_rated in range(
            args.power_output_rated_start, 
            args.power_output_rated_end + args.power_output_rated_increment, 
            args.power_output_rated_increment
        )
        if power_output_rated <= energy_capacity_rated
    ]

    # OTHER FIXED ARGS
    global state_of_health, state_of_charge_initial, state_of_charge_minimum, state_of_charge_maximum
    global self_discharge_rate, efficiency_charge, efficiency_discharge, rest_before_charge, rest_after_discharge
    state_of_health = args.state_of_health
    state_of_charge_initial = args.state_of_charge_initial
    state_of_charge_minimum = args.state_of_charge_minimum
    state_of_charge_maximum = args.state_of_charge_maximum
    self_discharge_rate = args.self_discharge_rate
    efficiency_charge = args.efficiency_charge
    efficiency_discharge = args.efficiency_discharge
    rest_before_charge = args.rest_before_charge
    rest_after_discharge = args.rest_after_discharge
    
    # PARALLEL COMPUTATION
    suppress_gurobi_parallel_spam()
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        net_arbitrage_revenues_per_config = list(
            executor.map(job_per_processor, range(len(pairs_per_config)))
        )

    update_monthly_csv(net_arbitrage_revenues_per_config, pairs_per_config, args)


if __name__=="__main__":
    main()