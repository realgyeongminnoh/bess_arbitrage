from pathlib import Path
import numpy as np


def get_datetime64(yyyymmdd: int, exclude: bool):
    year, month, day = [str(yyyymmdd)[i:j] for i, j in [(0, 4), (4, 6), (6, 8)]]
    time = np.datetime64(f"{year}-{month}-{day}", "h")
    time -= np.timedelta64(1, "h") if exclude else 0
    return time


def get_smp(time_start: np.datetime64, time_end: np.datetime64, is_historical: bool):
    file_name_end = "historical.npy" if is_historical else "forecasted.npy"
    dir_data_inputs = Path(__file__).resolve().parents[1] / "data" / "inputs"

    timestamp = np.load(dir_data_inputs / ("timestamp_" + file_name_end))
    time_start_idx, time_end_idx = tuple([int(np.where(timestamp == time)[0][0]) for time in [time_start, time_end]])
    smp = np.load(dir_data_inputs / ("smp_" + file_name_end))[time_start_idx: time_end_idx+1]
    return smp