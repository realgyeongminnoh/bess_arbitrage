import csv
import numpy as np
from pathlib import Path


def convert_date_int_to_datetime64(date_int: int, is_date_end: bool):
    date_string = str(date_int)
    time = np.datetime64(f"{date_string[:4]}-{date_string[4:6]}-{date_string[6:]}T00")
    time += np.timedelta64(23, "h") if is_date_end else 0
    return time


def get_smp(time_horizon_idx: int, time_start: np.datetime64, time_end: np.datetime64):
    path_time_horizon_folder = Path(__file__).resolve().parents[1] / "data" / "inputs" / f"time_horizon_{time_horizon_idx}"
    timestamp_full = np.load(path_time_horizon_folder / "timestamp.npy")
    idx_start, idx_end = int(np.where(timestamp_full == time_start)[0][0]), int(np.where(timestamp_full == time_end)[0][0])
    return np.load(path_time_horizon_folder / "smp.npy")[idx_start:idx_end + 1]


def save_custom_output(time_start, time_end, args, output):
    path_custom_folder = Path(__file__).resolve().parents[1] / "data" / "outputs" / "custom"
    path_custom_detail_folder = path_custom_folder / "detail"
    path_custom_folder.mkdir(parents=True, exist_ok=True)
    path_custom_detail_folder.mkdir(parents=True, exist_ok=True)
    path_csv_file = path_custom_folder / "result.csv"

    if not path_csv_file.exists():

        header = [
            "time_start",
            "time_end",
            "custom_idx",
            "return_detail",
            "use_smp_ref",
            "time_horizon_idx_smp",
            "time_horizon_idx_smp_ref",
            "discharging_revenue",
            "charging_cost",
            "arbitrage_profit",
            "ecr",
            "por",
            "soh",
            "soc_ini",
            "soc_min",
            "soc_max",
            "sdr",
            "ec",
            "ed",
            "rbc",
            "rad",
        ]

        with path_csv_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)

    with path_csv_file.open("r") as f:
        custom_idx = sum(1 for _ in f) - 1

    row = [
        time_start,
        time_end,
        custom_idx,
        args.return_detail,
        args.use_smp_ref,
        args.time_horizon_idx_smp,
        args.time_horizon_idx_smp_ref if args.use_smp_ref else args.time_horizon_idx_smp,
        output.discharging_revenue,
        output.charging_cost,
        output.arbitrage_profit,
        args.ecr,
        args.por,
        args.soh,
        args.soc_ini,
        args.soc_min,
        args.soc_max,
        args.sdr,
        args.ec,
        args.ed,
        args.rbc,
        args.rad,
    ]

    with path_csv_file.open("a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    if args.return_detail:
        np.save(path_custom_detail_folder / f"{custom_idx}.npy", output.detail)