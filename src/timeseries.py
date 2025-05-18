from pathlib import Path
import numpy as np


def get_datetime64(yyyymmdd: int):
    year, month, day = [str(yyyymmdd)[i:j] for i, j in [(0, 4), (4, 6), (6, 8)]]
    time = np.datetime64(f"{year}-{month}-{day}", "h")
    return time


def get_smp(time_start: np.datetime64, time_end: np.datetime64, is_historical: bool):
    historical_or_forecasted = "historical" if is_historical else "forecasted"
    dir_data_inputs = Path(__file__).resolve().parents[1] / "data" / "inputs" / historical_or_forecasted

    timestamps = np.load(dir_data_inputs / "timestamps.npy")
    time_start_idx, time_end_idx = tuple([int(np.where(timestamps == time)[0][0]) for time in [time_start, time_end]])
    smp = np.load(dir_data_inputs / "system_marginal_prices.npy")[time_start_idx: time_end_idx+1]
    return smp