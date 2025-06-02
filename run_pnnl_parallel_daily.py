import os
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from src.parameter import Parameter
from src.operation_optimization import optimize
from src.utils import get_smp, suppress_gurobi_parallel_spam


def parse_args():
    parser = argparse.ArgumentParser()
    # time-related
    parser.add_argument("--time_horizon_idx_smp", "--thi_smp", type=int, required=True)
    parser.add_argument("--time_horizon_idx_smp_ref", "--thi_smp_ref", type=int, default=0)
    # solver bool flags
    parser.add_argument("--use_smp_ref", "--usr", action="store_true")
    # others
    parser.add_argument("--only_lfp", "--lfp", action="store_true")

    return parser.parse_args()


def get_smp_daily(args):
    root = Path(__file__).resolve().parents[0] / "data" / "inputs" / f"time_horizon_{args.time_horizon_idx_smp}"
    timestamp = np.load(root / "timestamp.npy")
    first_day = timestamp[0].astype("datetime64[D]")
    last_day  = timestamp[-1].astype("datetime64[D]")

    ts_daily = np.arange(first_day, last_day + np.timedelta64(1, "D"), dtype="datetime64[D]")

    global timestamp_yearly_str, num_periods, num_years, smp_daily, smp_ref_daily, period_to_year

    timestamp_yearly_str = pd.to_datetime(ts_daily).year.astype(str).unique().tolist()
    num_days = len(ts_daily)
    num_years = len(timestamp_yearly_str)

    smp_list = []
    period_to_year = []
    for d in ts_daily:
        start_h = d.astype("datetime64[h]")
        end_h   = (d + np.timedelta64(1, "D")).astype("datetime64[h]") - np.timedelta64(1, "h")
        smp_arr = get_smp(args.time_horizon_idx_smp, start_h, end_h)
        smp_list.append(smp_arr)
        period_to_year.append(str(d.astype("datetime64[Y]").astype(int) + 1970))

    smp_daily = smp_list

    if args.use_smp_ref:
        smp_ref_list = []
        for d in ts_daily:
            start_h = d.astype("datetime64[h]")
            end_h   = (d + np.timedelta64(1, "D")).astype("datetime64[h]") - np.timedelta64(1, "h")
            smp_arr_ref = get_smp(args.time_horizon_idx_smp_ref, start_h, end_h)
            smp_ref_list.append(smp_arr_ref)
        smp_ref_daily = smp_ref_list
    else:
        smp_ref_daily = None

    num_periods = num_days


def job_per_processor(idx_day):
    smp_arr = smp_daily[idx_day]
    smp_ref_arr = smp_ref_daily[idx_day] if use_smp_ref else None
    return optimize(
        parameter=parameter,
        smp=smp_arr,
        smp_ref=smp_ref_arr,
        return_detail=False,
    )


def per_csv(path_inputs_csv_file, path_outputs_csv_file_profit, path_outputs_csv_file_revenue):
    arr_configs = pd.read_csv(path_inputs_csv_file, header=0).to_numpy()
    num_configs = arr_configs.shape[0]

    arbitrage_profit = np.empty((num_configs, num_periods))
    discharging_revenue = np.empty((num_configs, num_periods))

    for idx_config, arr_config in enumerate(arr_configs):
        global parameter
        parameter = Parameter(
            ecr=int(arr_config[0]),
            por=int(arr_config[1]),
            soh=1,
            soc_ini=arr_config[2],
            soc_min=arr_config[2],
            soc_max=arr_config[3],
            sdr=0,
            ec=arr_config[4],
            ed=arr_config[4],
            rbc=int(arr_config[5]),
            rad=int(arr_config[5]),
        )

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            outputs = list(executor.map(job_per_processor, range(num_periods)))

        arbitrage_profit[idx_config, :]   = [out.arbitrage_profit   for out in outputs]
        discharging_revenue[idx_config, :] = [out.discharging_revenue for out in outputs]

    df_profit  = pd.DataFrame(arbitrage_profit,   columns=period_to_year)
    df_revenue = pd.DataFrame(discharging_revenue, columns=period_to_year)

    annual_profit  = df_profit.groupby(axis=1, level=0).sum().astype(int)
    annual_revenue = df_revenue.groupby(axis=1, level=0).sum().astype(int)

    annual_profit.to_csv(path_outputs_csv_file_profit, index=False)
    annual_revenue.to_csv(path_outputs_csv_file_revenue, index=False)


def main():
    args = parse_args()
    get_smp_daily(args)
    suppress_gurobi_parallel_spam()
    global use_smp_ref
    use_smp_ref = args.use_smp_ref

    names_csv_file = [
        "Lithium-ion_LFP_2023_Neutral.csv",
        "Lithium-ion_LFP_2030_Neutral.csv",
        "Lithium-ion_LFP_2030_Optimistic.csv",
        "Lithium-ion_LFP_2030_Pessimistic.csv",
    ]
    if not args.only_lfp:
        names_csv_file += [
            "Lithium-ion_NMC_2023_Neutral.csv",
            "Lead_Acid_2023_Neutral.csv",
            "Vanadium_Redox_Flow_2023_Neutral.csv",
        ]

    path_inputs_pnnl_folder = Path(__file__).resolve().parents[0] / "data" / "inputs" / "pnnl"
    path_outputs_pnnl_folder = (
        Path(__file__).resolve().parents[0] / "data" / "outputs" / "pnnl" /
        f"time_horizon_{args.time_horizon_idx_smp}_ref_{(args.time_horizon_idx_smp_ref if use_smp_ref else args.time_horizon_idx_smp)}"
    )
    path_outputs_pnnl_folder.mkdir(parents=True, exist_ok=True)

    for name_csv_file in names_csv_file:
        path_inputs_csv_file         = path_inputs_pnnl_folder / name_csv_file
        path_outputs_csv_file_profit = path_outputs_pnnl_folder / (name_csv_file[:-4] + "_profit.csv")
        path_outputs_csv_file_revenue= path_outputs_pnnl_folder / (name_csv_file[:-4] + "_revenue.csv")
        per_csv(path_inputs_csv_file, path_outputs_csv_file_profit, path_outputs_csv_file_revenue)


if __name__ == "__main__":
    main()