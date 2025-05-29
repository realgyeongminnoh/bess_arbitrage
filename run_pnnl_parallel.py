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


def get_smp_monthly(args):
    timestamp = np.load(Path(__file__).resolve().parents[0] / "data" / "inputs" / f"time_horizon_{args.time_horizon_idx_smp}" / "timestamp.npy")
    timestamp_monthly = np.arange(timestamp[0].astype("datetime64[M]"), (timestamp[-1] + 1).astype("datetime64[M]"))

    global timestamp_yearly_str, num_months, num_years, smp_monthly, smp_ref_monthly
    timestamp_yearly_str = np.arange(timestamp[0].astype("datetime64[Y]"), (timestamp[-1] + 1).astype("datetime64[Y]")).astype(str).tolist()
    num_months = len(timestamp_monthly)
    num_years = num_months // 12
    smp_monthly = [
        get_smp(args.time_horizon_idx_smp, time_month_start, time_month_end)
        for time_month_start, time_month_end in
        zip(timestamp_monthly.astype("datetime64[h]"), (timestamp_monthly + 1) - np.timedelta64(1, "h"))
    ]
    smp_ref_monthly = [
        get_smp(args.time_horizon_idx_smp_ref, time_month_start, time_month_end)
        for time_month_start, time_month_end in
        zip(timestamp_monthly.astype("datetime64[h]"), (timestamp_monthly + 1) - np.timedelta64(1, "h"))
    ] if args.use_smp_ref else None


def job_per_processor(idx_month):
    return optimize(
        parameter=parameter,
        smp=smp_monthly[idx_month],
        smp_ref=smp_ref_monthly[idx_month] if use_smp_ref else None,
        return_detail=False,
    )


def per_csv(path_inputs_csv_file, path_outputs_csv_file_profit, path_outputs_csv_file_revenue):
    arr_configs = pd.read_csv(path_inputs_csv_file, header=0).to_numpy()
    num_configs = arr_configs.shape[0]
    arbitrage_profit = np.empty((num_configs, num_months))
    discharging_revenue = np.empty((num_configs, num_months))

    # loop by config
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

        # parallel by month
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            outputs = list(
                executor.map(job_per_processor, range(num_months))
            )
 
        # save on ram by config
        arbitrage_profit[idx_config] = [output.arbitrage_profit for output in outputs]
        discharging_revenue[idx_config] = [output.discharging_revenue for output in outputs]

    # save on disk by config x year
    pd.DataFrame(
        arbitrage_profit.reshape(num_configs, num_years, 12).sum(axis=2).astype(int),
        columns=timestamp_yearly_str,
    ).to_csv(path_outputs_csv_file_profit, index=False)
    pd.DataFrame(
        discharging_revenue.reshape(num_configs, num_years, 12).sum(axis=2).astype(int),
        columns=timestamp_yearly_str,
    ).to_csv(path_outputs_csv_file_revenue, index=False)


def main():
    args = parse_args()
    get_smp_monthly(args)
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

    path_inputs_pnnl_folder = Path.cwd() / "data" / "inputs" / "pnnl"
    path_outputs_pnnl_folder = (
        Path.cwd() / "data" / "outputs" / "pnnl" / 
        f"time_horizon_{args.time_horizon_idx_smp}_ref_{args.time_horizon_idx_smp_ref if use_smp_ref else args.time_horizon_idx_smp}"
    )
    path_outputs_pnnl_folder.mkdir(parents=True, exist_ok=True)

    # loop by csv
    for name_csv_file in names_csv_file:
        path_inputs_csv_file = path_inputs_pnnl_folder / name_csv_file
        path_outputs_csv_file_profit = path_outputs_pnnl_folder / (name_csv_file[:-4] + "_profit.csv")
        path_outputs_csv_file_revenue = path_outputs_pnnl_folder / (name_csv_file[:-4] + "_revenue.csv")

        per_csv(path_inputs_csv_file, path_outputs_csv_file_profit, path_outputs_csv_file_revenue)


if __name__=="__main__":
    main()