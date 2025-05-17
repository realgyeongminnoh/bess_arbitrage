import argparse
from pathlib import Path
import csv
import numpy as np

from src.timeseries import get_datetime64


def parse_args():
    parser = argparse.ArgumentParser(description="run this before anything")
    parser.add_argument("--is_historical", "--ih", action="store_true", help="historical -> --ih")
    parser.add_argument("--full_month_start", "--fms", type=int, required=True, help="yyyymm; ex) 2015.01.01 -> \"--fms 201501\"")
    parser.add_argument("--full_month_end", "--fme", type=int, required=True, help="yyyymm; ex) 2024.12.31 -> \"--fme 202501\"")
    return parser.parse_args()


def validate_args(args):
    if not (200001 <= args.full_month_start):
        raise ValueError(f"200001 <= {args.full_month_start} = full_month_start")
    if not (args.full_month_end <= 300001):
        raise ValueError(f"full_month_end = {args.full_month_end} < 300001")
    if not (args.full_month_start < args.full_month_end):
        raise ValueError(f"full_month_start = {args.full_month_start} < {args.full_month_end} = full_month_end")


def save_timestamps(full_date_start, full_date_end, historical_or_forecasted):
    timestamps = np.arange(
        full_date_start,
        full_date_end + np.timedelta64(1, "h")
        )

    timestamps_length = timestamps.shape[0]
    
    # TIMESTAMPS SMP LENGTH CHECK
    dir_inputs = Path(__file__).resolve().parents[0] / "data" / "inputs" / historical_or_forecasted
    system_marginal_prices_length = np.load(dir_inputs / "system_marginal_prices.npy").shape[0]
    if not (timestamps_length == system_marginal_prices_length):
        raise ValueError(
        "Check full date start and end (end date = 1 + last date of hourly SMP)\n"
        "Hourly timestamps created based on full date start and end passed as arguments\n"
        f"do not have the same length as hourly system marginal prices in / data / inputs / {historical_or_forecasted} /"
        )
    
    np.save(dir_inputs / "timestamps.npy", timestamps)
    print("timestamps initialized for the given system marginal prices")


def create_csvs(full_month_start, full_month_end, historical_or_forecasted):
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

    count_init, count_exist = 0, 0
    for start_month in [month for month in range(full_month_start, full_month_end) if 1 <= month % 100 <= 12]:
        path_csv = dir_csvs / f"{start_month}.csv"

        if not path_csv.exists():
            with path_csv.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
            count_init += 1
        else:
            count_exist += 1

    print(f"{count_init} csvs wereinitialized, {count_exist} csvs existed for each month in {full_month_start} ~ {start_month}")
    
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
    full_date_start = get_datetime64(args.full_month_start * 100 + 1, False)
    full_date_end = get_datetime64(args.full_month_end * 100 + 1, True)

    save_timestamps(full_date_start, full_date_end, historical_or_forecasted)
    create_csvs(args.full_month_start, args.full_month_end, historical_or_forecasted)


if __name__=="__main__":
    main()