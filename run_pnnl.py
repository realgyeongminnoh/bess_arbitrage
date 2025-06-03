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
    parser = argparse.ArgumentParser(description="[dataset] 1: 2015-2024 historical, 2: 2024 (historical), 3: 2024 (forecasted daily)")
    # dataset related
    parser.add_argument("--dataset_idx_opt", "--dio", type=int, required=True, help="select dataset for operation optimization")
    parser.add_argument("--dataset_idx_rev", "--dir", type=int, required=True, help="select dataset for revenue-related computation")
    # time horizon
    parser.add_argument("--time_horizon", "--th", type=str, required=True, help="[time horizon for operation optimization] D: daily, M: monthly")
    return parser.parse_args()


def get_smp_time_horizon_ly(args):
    timestamp = np.load(Path.cwd() / "data" / "inputs" / f"dataset_{args.dataset_idx_opt}" / "timestamp.npy")

    global years_str, num_years
    years_npdatetime = np.arange(timestamp[0].astype("datetime64[Y]"), (timestamp[-1] + 1).astype("datetime64[Y]"))
    years_str = years_npdatetime.astype(str).tolist()
    num_years = len(years_str)

    timestamp_time_horizon_ly = np.arange(
        timestamp[0].astype(f"datetime64[{args.time_horizon[-1]}]"),
        (timestamp[-1] + 1).astype(f"datetime64[{args.time_horizon[-1]}]")
    )
    timestamp_time_horizon_ly_per_year = [
        timestamp_time_horizon_ly[timestamp_time_horizon_ly.astype("datetime64[Y]") == yr]
        for yr in years_npdatetime
    ]
    time_step_time_horizon_ly = np.timedelta64(1, args.time_horizon[-1])

    global num_time_horizons_per_year
    num_time_horizons_per_year = [
        len(timestamp_time_horizon_ly_single_year) 
        for timestamp_time_horizon_ly_single_year 
        in timestamp_time_horizon_ly_per_year
    ]

    global smp_per_time_horizon_per_year_opt
    smp_per_time_horizon_per_year_opt = [
        [
            get_smp(
                args.dataset_idx_opt,
                timestamp_time_horizon_ly_per_time_horizon.astype("datetime64[h]"),
                (timestamp_time_horizon_ly_per_time_horizon + time_step_time_horizon_ly) - np.timedelta64(1, "h")
            )
            for timestamp_time_horizon_ly_per_time_horizon 
            in timestamp_time_horizon_ly_single_year
        ]
        for timestamp_time_horizon_ly_single_year 
        in timestamp_time_horizon_ly_per_year
    ]

    global smp_per_time_horizon_per_year_rev
    smp_per_time_horizon_per_year_rev = [
        [
            get_smp(
                args.dataset_idx_rev,
                timestamp_time_horizon_ly_per_time_horizon.astype("datetime64[h]"),
                (timestamp_time_horizon_ly_per_time_horizon + time_step_time_horizon_ly) - np.timedelta64(1, "h")
            )
            for timestamp_time_horizon_ly_per_time_horizon 
            in timestamp_time_horizon_ly_single_year
        ]
        for timestamp_time_horizon_ly_single_year 
        in timestamp_time_horizon_ly_per_year
    ] if (args.dataset_idx_rev != args.dataset_idx_opt) else None


def job_per_processor(idx_time_horizon):
    return optimize(
        parameter=parameter,
        smp_opt=smp_per_time_horizon_per_year_opt[idx_year][idx_time_horizon],
        smp_rev=smp_per_time_horizon_per_year_rev[idx_year][idx_time_horizon] if (smp_per_time_horizon_per_year_rev is not None) else None,
        return_detail=False,
    )


def per_input_csv(
    path_inputs_csv_file, 
    path_outputs_csv_file_bess_revenue_generation, 
    path_outputs_csv_file_plant_revenue_reduction,
    path_outputs_csv_file_combined_revenue_net,
):
    arr_configs = pd.read_csv(path_inputs_csv_file, header=0).to_numpy()
    num_configs = arr_configs.shape[0]

    bess_revenue_generation_yearly = np.empty((num_configs, num_years))
    plant_revenue_reduction_yearly = np.empty((num_configs, num_years))
    combined_revenue_net_yearly = np.empty((num_configs, num_years))

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

        for idx_year_loopvar, num_time_horizons in enumerate(num_time_horizons_per_year):
            global idx_year
            idx_year = idx_year_loopvar

            with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
                outputs = list(
                    executor.map(job_per_processor, range(num_time_horizons))
                )
 
            # save on ram by config x year (summed by time horizon in the year)
            bess_revenue_generation_yearly[idx_config, idx_year] = sum(output.bess_revenue_generation for output in outputs)
            plant_revenue_reduction_yearly[idx_config, idx_year] = sum(output.plant_revenue_reduction for output in outputs)
            combined_revenue_net_yearly[idx_config, idx_year] = sum(output.combined_revenue_net for output in outputs)

    # save on disk by config x year
    pd.DataFrame(
        bess_revenue_generation_yearly.astype(int), columns=years_str,
    ).to_csv(path_outputs_csv_file_bess_revenue_generation, index=False)
    pd.DataFrame(
        plant_revenue_reduction_yearly.astype(int), columns=years_str,
    ).to_csv(path_outputs_csv_file_plant_revenue_reduction, index=False)
    pd.DataFrame(
        combined_revenue_net_yearly.astype(int), columns=years_str,
    ).to_csv(path_outputs_csv_file_combined_revenue_net, index=False)


def main():
    suppress_gurobi_parallel_spam()
    
    global time_horizon
    args = parse_args()
    time_horizon = args.time_horizon
    get_smp_time_horizon_ly(args)

    # folder path
    path_inputs_pnnl_folder = Path(__file__).resolve().parents[0] / "data" / "inputs" / "pnnl"
    path_outputs_pnnl_folder = (
        Path(__file__).resolve().parents[0] / "data" / "outputs" / f"pnnl_{time_horizon}" / 
        f"opt_{args.dataset_idx_opt}_rev_{args.dataset_idx_rev}"
    )
    path_outputs_pnnl_folder.mkdir(parents=True, exist_ok=True)

    # pnnl input csv file names
    names_csv_file = [
        "Lithium-ion_LFP_2023_Neutral.csv",
        "Lithium-ion_LFP_2030_Neutral.csv",
        "Lithium-ion_LFP_2030_Optimistic.csv",
        "Lithium-ion_LFP_2030_Pessimistic.csv",
        "Lithium-ion_NMC_2023_Neutral.csv",
        "Lead_Acid_2023_Neutral.csv",
        "Vanadium_Redox_Flow_2023_Neutral.csv",
    ]

    # loop by pnnl input csv files
    for name_csv_file in names_csv_file:
        path_inputs_csv_file = path_inputs_pnnl_folder / name_csv_file
        path_outputs_csv_file_bess_revenue_generation = path_outputs_pnnl_folder / (name_csv_file[:-4] + "_bess_revenue_generation.csv")
        path_outputs_csv_file_plant_revenue_reduction = path_outputs_pnnl_folder / (name_csv_file[:-4] + "_plant_revenue_reduction.csv")
        path_outputs_csv_file_combined_revenue_net = path_outputs_pnnl_folder / (name_csv_file[:-4] + "_combined_revenue_net.csv")

        per_input_csv(
            path_inputs_csv_file, 
            path_outputs_csv_file_bess_revenue_generation, 
            path_outputs_csv_file_plant_revenue_reduction,
            path_outputs_csv_file_combined_revenue_net,
        )


if __name__=="__main__":
    main()