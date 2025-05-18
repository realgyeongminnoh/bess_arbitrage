import argparse
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from src.timeseries import get_datetime64, get_smp


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--is_historical", "--ih", action="store_true")
    parser.add_argument("--month_start", "--ms", type=int, required=True, help="yyyymm; ex) 2022.01.01 -> \"--fms 202201\"")
    parser.add_argument("--month_end", "--me", type=int, required=True, help="yyyymm; ex) 2022.01.31 -> \"--fme 202202\"")




    return parser.parse_args()


def validate_args(args):
    # time-related args
    if (not args.is_historical):
        raise NotImplementedError()
    if not (args.month_start < args.month_end):
        raise ValueError(f"month_start = {args.month_start} < {args.month_end} = month_end")
        
    historical_or_forecasted = "historical" if args.is_historical else "forecasted"    
    timestamps = np.load(Path(__file__).resolve().parents[0] / "data" / "inputs" / historical_or_forecasted / "timestamps.npy")
    full_month_start = int(str(timestamps[0])[:7].replace("-", ""))
    full_month_end = int(str(timestamps[-1] + np.timedelta64(1, "h"))[:7].replace("-", ""))

    if not (full_month_start <= args.month_start):
        raise ValueError(f"full_month_start from initialization (timestamps) = {full_month_start} <= {args.month_start} = month_start")
    if not (args.month_end <= full_month_end):
        raise ValueError(f"month_end = {args.month_end} <= {full_month_end} = full_month_end from initialization (timestamps)")

    # other args



def main():
    args = parse_args()
    validate_args(args)

    
    time_start = get_datetime64(args.month_start * 100 + 1, False)
    time_end = get_datetime64(args.month_end * 100 + 1, True)
    time_horizon_length = int((time_end - time_start + 1).astype(int))    
    system_marginal_price = get_smp(time_start, time_end, args.is_historical)



main()