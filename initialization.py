import argparse
from pathlib import Path
import csv
import numpy as np

from src.timeseries import get_datetime64


def parse_args():
    parser = argparse.ArgumentParser(description="im not getting paid for this so please just full year(s) hourly SMP")
    parser.add_argument("--is_historical", "--ih", action="store_true", help="historical -> --ih")
    parser.add_argument("--full_year_start", "--hds", type=int, required=True, help="yyyy; ex) 2015.01.01 -> \"--hds 2015\"")
    parser.add_argument("--full_year_end", "--hde", type=int, required=True, help="yyyy; ex) 2024.12.31 -> \"--hde 2025\"")
    return parser.parse_args()


def validate_args(args):
    if not (2000 <= args.full_year_start):
        raise ValueError(f"2000 <= {args.full_year_start} = full_year_start")
    if not (args.full_year_end < 3000):
        raise ValueError(f"full_year_end = {args.full_year_end} < 3000")
    if not (args.full_year_start < args.full_year_end):
        raise ValueError(f"full_year_start = {args.full_year_start} < {args.full_year_end} = full_year_end")


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


def create_csvs(full_year_start, full_year_end, historical_or_forecasted):
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

    pairs_month = [
        (
            (y * 10000 + m * 100 + 1),
            ((y + (m == 12)) * 10000 + ((m % 12) + 1) * 100 + 1),
        )
        for y in range(full_year_start, full_year_end)
        for m in range(1, 13)
    ]

    for pair_month in pairs_month:
        path_csv = dir_csvs / f"{pair_month[0]}_{pair_month[1]}.csv"
        
        if not path_csv.exists():
            with path_csv.open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)

    print(f"{len(pairs_month)} csvs initialized (or already exist) for each month in {full_year_start} ~ {full_year_end - 1}")
    
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
    full_date_start = get_datetime64(args.full_year_start * 10000 + 101, False)
    full_date_end = get_datetime64(args.full_year_end * 10000 + 101, True)

    save_timestamps(full_date_start, full_date_end, historical_or_forecasted)
    create_csvs(args.full_year_start, args.full_year_end, historical_or_forecasted)


if __name__=="__main__":
    main()