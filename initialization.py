import csv
import argparse
import numpy as np
from pathlib import Path

from src.timeseries import get_datetime64


def parse_args():
    parser = argparse.ArgumentParser(description="run this before anything; SMP given must be monthly (the end must include SMP of the end date and hour of the month)")
    parser.add_argument("--is_historical", "--ih", action="store_true", help="historical -> --ih")
    parser.add_argument("--complete_month_start", "--cms", type=int, required=True, help="yyyymm; ex) 2015.01.01 -> \"--cms 201501\"")
    parser.add_argument("--complete_month_end", "--cme", type=int, required=True, help="yyyymm; ex) 2024.12.31 -> \"--cme 202412\"")
    return parser.parse_args()


def validate_args(args):
    if (not args.is_historical):
        raise NotImplementedError()
    if not (200001 <= args.complete_month_start):
        raise ValueError(f"200001 <= {args.complete_month_start} = complete_month_start")
    if not (args.complete_month_end <= 300001):
        raise ValueError(f"complete_month_end = {args.complete_month_end} < 300001")
    if not (args.complete_month_start <= args.complete_month_end):
        raise ValueError(f"complete_month_start = {args.complete_month_start} <= {args.complete_month_end} = complete_month_end")


def save_timestamps(complete_date_start, complete_date_end, historical_or_forecasted):
    timestamps = np.arange(
        complete_date_start,
        complete_date_end + np.timedelta64(1, "h")
    )

    timestamps_length = timestamps.shape[0]

    # TIMESTAMPS SMP LENGTH CHECK
    dir_inputs = Path(__file__).resolve().parents[0] / "data" / "inputs" / historical_or_forecasted
    system_marginal_prices_length = np.load(dir_inputs / "system_marginal_prices.npy").shape[0]
    if not (timestamps_length == system_marginal_prices_length):
        raise ValueError(
        "Check full date start and end\n"
        "(SMP must be monthly; the end must include SMP of the end hour of the month)\n"
        "Hourly timestamps created based on full date start and end passed as arguments\n"
        f"do not have the same length as hourly system marginal prices in / data / inputs / {historical_or_forecasted} /"
        )
    
    np.save(dir_inputs / "timestamps.npy", timestamps)
    print(f"timestamps initialized for the given system marginal prices; range: {timestamps[0]} ~ {timestamps[-1]}")


def create_csvs(complete_date_start, complete_date_end, historical_or_forecasted):
    dir_outputs = Path(__file__).resolve().parents[0] / "data" / "outputs" / historical_or_forecasted

    # MONTHLY
    header = [
        "net_arbitrage_revenue",
        "energy_capacity_rated",
        "power_output_rated",
        "state_of_health",
        "state_of_charge_initial",
        "state_of_charge_minimum",
        "state_of_charge_maximum",
        "self_discharge_rate",
        "efficiency_charge",
        "efficiency_discharge",
        "rest_before_charge",
        "rest_after_discharge",
    ]

    dir_csvs = dir_outputs / "net_arbitrage_revenues"
    dir_csvs.mkdir(parents=True, exist_ok=True)

    months = [   
        str(np_yyyy_mm).replace("-", "")
        for np_yyyy_mm in
        np.arange(complete_date_start.astype("datetime64[M]"), (complete_date_end + np.timedelta64(1, "h")).astype("datetime64[M]"))
    ]

    count_init, count_exist = 0, 0
    for month in months:
        path_csv = dir_csvs / f"{month}.csv"

        if not path_csv.exists():
            with path_csv.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
            count_init += 1
        else:
            count_exist += 1

    print(f"{count_init} csvs were initialized, {count_exist} csvs existed; for each month in {months[0]} ~ {months[-1]}")
    
    # MISCELLANEOUS
    header_miscellaneous = header + [
        "return_details",
        "miscellaneous_index",
        "date_start",
        "date_end",
    ]

    dir_details = dir_outputs / "details_miscellaneous"
    dir_details.mkdir(parents=True, exist_ok=True)
    path_csv = dir_csvs / "miscellaneous.csv"

    if not path_csv.exists():
        with path_csv.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header_miscellaneous)

        print(f"miscellaneous.csv initialized for non-monthly optimization results")
    else:
        print(f"miscellaneous.csv exists for non-monthly optimization results")


def main():
    args = parse_args()
    validate_args(args)

    historical_or_forecasted = "historical" if args.is_historical else "forecasted"
    complete_date_start = get_datetime64(args.complete_month_start * 100 + 1)
    complete_date_end = np.datetime64(get_datetime64(args.complete_month_end * 100 + 1).astype("datetime64[M]") + 1, "h") - np.timedelta64(1, "h")

    save_timestamps(complete_date_start, complete_date_end, historical_or_forecasted)
    create_csvs(complete_date_start, complete_date_end, historical_or_forecasted)


if __name__=="__main__":
    main()