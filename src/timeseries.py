from pathlib import Path
import numpy as np


class Timeseries:
    def __init__(
            self, 
            is_minute: bool, 
            is_historical: bool, 
            end_exclude: bool, 
            time_start: int, 
            time_end: int
    ):

        self.is_minute = is_minute
        self.is_historical = is_historical
        self.end_exclude = end_exclude

        self._file_smp = "smp_historical.npy" if self.is_historical else "smp_forecasted.npy"
        self._file_timestamp = "timestamp_historical.npy" if self.is_historical else "timestamp_forecasted.npy"
        self._dir_data_inputs = Path(__file__).resolve().parents[1] / "data" / "inputs"

        self.time_start: np.datetime64 = self.get_datetime64(time_start)
        self.time_end: np.datetime64 = self.get_datetime64(time_end, exclude=end_exclude)
        
        self.timestamp = np.load(self._dir_data_inputs / self._file_timestamp)
        self.smp = np.load(self._dir_data_inputs / self._file_smp)
        self.hour_count: int = int((self.time_end - self.time_start + 1).astype(int))
        self.minute_count: int = self.hour_count * 60
        if self.is_minute:
            self.timestamp = np.array([ts + np.arange(60).astype("timedelta64[m]") for ts in self.timestamp]).reshape(-1)
            self.smp = np.repeat(self.smp / 60, 60)
            self.minute_count: int = int((self.time_end - self.time_start + 1).astype(int))
            self.hour_count: int = self.minute_count // 60

        
        time_start_idx, time_end_idx = tuple([int(np.where(self.timestamp == time)[0][0]) for time in [self.time_start, self.time_end]])
        self.timestamp = self.timestamp[time_start_idx:time_end_idx+1]
        self.smp = self.smp[time_start_idx:time_end_idx+1]

    
    def get_datetime64(self, yyyymmddhh:int, exclude:bool=False, minute:int = 0):
        year, month, day, hour = map(int, [str(yyyymmddhh).zfill(10)[i:j] for i, j in [(0,4), (4,6), (6,8), (8,10)]])
        time = np.datetime64(f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}", "h")
        time += np.timedelta64(int(minute), "m") if self.is_minute else 0
        time -= (np.timedelta64(1, "m") if self.is_minute else np.timedelta64(1, "h")) if exclude else 0
        return time