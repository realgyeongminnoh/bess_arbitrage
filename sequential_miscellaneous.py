import argparse
import numpy as np
from pathlib import Path

from src.timeseries import get_datetime64, get_smp
from src.solver import optimize
from src.utils import update_miscellaneous_csv


def parse_args():
    parser = argparse.ArgumentParser()
    # TIME-RELATED ARGS
    parser.add_argument("--is_historical", "--ih", action="store_true")
    parser.add_argument("--date_start", "--ds", type=int, required=True, help="yyyymmdd; ex) 2022.01.01 -> \"--ds 20220101\"")
    parser.add_argument("--date_end", "--de", type=int, required=True, help="yyyymmdd; ex) 2022.01.31 -> \"--ds 20220131\"") 
    # OTHER FIXED ARGS
    parser.add_argument("--energy_capacity_rated", "--ecr", type=int, required=True, help="energy capacity, rated; kWh")
    parser.add_argument("--power_output_rated", "--por", type=int, required=True, help="power output, rated; kW")
    parser.add_argument("--state_of_health", "--soh", type=float, required=False, default=1, help="state of health; pu; fixed")
    parser.add_argument("--state_of_charge_initial", "--socini", type=float, required=False, default=0, help="state of charge initial; pu")
    parser.add_argument("--state_of_charge_minimum", "--socmin", type=float, required=False, default=0, help="state of charge minimum; pu")
    parser.add_argument("--state_of_charge_maximum", "--socmax", type=float, required=False, default=1, help="state of charge maximum; pu")
    parser.add_argument("--self_discharge_rate", "--sdr", type=float, required=False, default=0, help="self-discharge rate; pu")
    parser.add_argument("--efficiency_charge", "--ec", type=float, required=False, default=1, help="efficiency charge; pu")
    parser.add_argument("--efficiency_discharge", "--ed", type=float, required=False, default=1, help="efficiency discharge; pu")
    parser.add_argument("--rest_before_charge", "--rbc", type=int, required=False, default=0, help="rest before charge; h; int")
    parser.add_argument("--rest_after_discharge", "--rad", type=int, required=False, default=0, help="rest after discharge; h; int")
    parser.add_argument("--return_details", "--rd", action="store_true")
    return parser.parse_args()


def validate_args(args):
    # TIME-RELATED ARGS
    if (not args.is_historical):
        raise NotImplementedError()
    if not (args.date_start <= args.date_end):
        raise ValueError(f"date_start = {args.date_start} <= {args.date_end} = date_end")

    historical_or_forecasted = "historical" if args.is_historical else "forecasted"    
    timestamps = np.load(Path(__file__).resolve().parents[0] / "data" / "inputs" / historical_or_forecasted / "timestamps.npy")
    complete_date_start = int(str(timestamps[0])[:10].replace("-", ""))
    complete_date_end = int(str(timestamps[-1])[:10].replace("-", ""))

    if not (complete_date_start <= args.date_start):
        raise ValueError(f"complete_date_start from initialization (timestamps) = {complete_date_start} <= {args.date_start} = date_start")
    if not (args.date_end <= complete_date_end):
        raise ValueError(f"date_end = {args.date_end} <= {complete_date_end} = complete_date_end from initialization (timestamps)")

    # OTHER FIXED ARGS
    if (args.energy_capacity_rated <= 0) or (args.power_output_rated <= 0) or (args.energy_capacity_rated < args.power_output_rated):
        raise ValueError("energy_capacity_rated / power_output_rated")
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


def main():
    args = parse_args()
    validate_args(args)

    time_start = get_datetime64(args.date_start)
    time_end = np.datetime64(get_datetime64(args.date_end).astype("datetime64[D]") + 1, "h") - np.timedelta64(1, "h") # T23

    time_horizon_length = int((time_end - time_start + 1).astype(int))    
    system_marginal_price = get_smp(time_start, time_end, args.is_historical)

    net_arbitrage_revenue, details = optimize(
        date_start=args.date_start,
        date_end=args.date_end,
        time_horizon_length=time_horizon_length,
        system_marginal_price=system_marginal_price,
        energy_capacity_rated=args.energy_capacity_rated,
        power_output_rated=args.power_output_rated,
        state_of_health=args.state_of_health,
        state_of_charge_initial=args.state_of_charge_initial,
        state_of_charge_minimum=args.state_of_charge_minimum,
        state_of_charge_maximum=args.state_of_charge_maximum,
        self_discharge_rate=args.self_discharge_rate,
        efficiency_charge=args.efficiency_charge,
        efficiency_discharge=args.efficiency_discharge,
        rest_before_charge=args.rest_before_charge,
        rest_after_discharge=args.rest_after_discharge,
        return_details=args.return_details,
    )

    update_miscellaneous_csv(net_arbitrage_revenue, details, args)


if __name__=="__main__":
    main()