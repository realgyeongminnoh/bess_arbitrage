import os
import argparse
import numpy as np
from concurrent.futures import ProcessPoolExecutor

from src import *
from src.utils import suppress_gurobi_parallel_spam, save_output


def parse_args():
    parser = argparse.ArgumentParser()
    # Timeseries args
    parser.add_argument("--is_minute", "--im", action="store_true", help="minute-level optimization granurality; otherwise hour-level")
    parser.add_argument("--is_historical", "--ih", action="store_true")
    parser.add_argument("--end_exclude", "--ee", action="store_true", help="time_end provided by --et is excluded")
    parser.add_argument("--time_start", "--ts", type=int, required=True, help="yyyymmddhh")
    parser.add_argument("--time_end", "--te", type=int, required=True, help="yyyymmddhh")
    # Parameter args
    parser.add_argument("--parameter_pnnl", "--pp", action="store_true", help="use parameter from PNNL database")
    parser.add_argument("--pnnl_technology", "--pt", type=str, required=False, default="Lithium-ion_LFP", help="(default=Lithium-ion_LFP)")
    parser.add_argument("--pnnl_year", "--py", type=int, required=False, default=2023, help="(default=2023)")
    parser.add_argument("--pnnl_estimate", "--pe", type=str, required=False, default="Point", help="(default=Point)")
    parser.add_argument("--pnnl_fxrate", "--fx", type=int, required=False, default=1333, help="FX rate of USDKRW as PNNL is in USD; (default=1333)")
    # Solver args
    parser.add_argument("--do_single", "--ds", action="store_true", help="perform only single configuration, otherwise multiple")
    parser.add_argument("--idx_config", "--ic", type=int, required=False, default=None, help="index of configuration fo rthe single configuration optimization")
    parser.add_argument("--do_efficiency", "--de", action="store_true", help="charging/discharging efficiency considered; otherwise efficiency=1")
    parser.add_argument("--do_rest", "--dr", action="store_true", help="rest before charge / rest after discharge considered; otherwise no rest")
    # multiple configuration args

    args = parser.parse_args()
    return args


def validate_args(args):
    # timeseries args
    if args.time_start >= args.time_end:
        raise ValueError("start time must be earlier than end time")
    if args.is_historical:
        if args.time_start < 2015010100:
            raise ValueError("time start must be 2015010100 or later")
        if args.end_exclude:
            if args.time_end > 2025010100:
                raise ValueError("time end muste be 2025010100 or earlier if end is to be excluded")
        else:
            if args.time_end > 2024123123:
                raise ValueError("time end muste be 2024123123 or earlier if end is to be included")
    else:
        raise NotImplementedError("not yet; forecasted SMP") # TBD

    # parameter args
    if args.parameter_pnnl: # checked for all Parameter elements of all unqiue configurations for each tech below
        if args.pnnl_technology not in ["Lithium-ion_LFP", "Lithium-ion_NMC", "Vanadium_Redox_Flow", "Lead_Acid", "Zinc"]:
            raise ValueError("for PNNL dataset, choose one: Lithium-ion_LFP, Lithium-ion_NMC, Vanadium_Redox_Flow, Lead_Acid, Zinc")
        if args.pnnl_year not in (2023, 2030):
            raise ValueError("PNNL dataset provides only 2023, 2030")
        if args.pnnl_estimate not in ["Point", "High", "Low"]:
            raise ValueError("for PNNL dataset, choose one: Point, High, Low")
        if not (1100 <= args.pnnl_fxrate <= 1500):
            raise ValueError("FX rate of USDKRW is not sensible")
    else:
        raise NotImplementedError("not yet: custom configuration") # TBD
    
    # solver args
    if (not args.do_single) and (args.idx_config is not None):
        raise ValueError("you cannot provide configuration index (--idx_single) with multiple configurations (no --do_single)")
    

def job(idx_config):
    solver = Solver(
        timeseries,
        parameter, 
        do_single=do_single,
        idx_config=idx_config,
        do_efficiency=do_efficiency,
        do_rest=do_rest,
    )

    return solver.solve()


def main():
    suppress_gurobi_parallel_spam()
    args = parse_args()
    validate_args(args)

    global timeseries
    timeseries = Timeseries(
        is_minute=args.is_minute, 
        is_historical=args.is_historical, 
        end_exclude=args.end_exclude, 
        time_start=args.time_start, 
        time_end=args.time_end
    )

    global parameter
    parameter = Parameter(
        timeseries,
        parameter_pnnl=args.parameter_pnnl,
        pnnl_technology=args.pnnl_technology,
        pnnl_year=args.pnnl_year, 
        pnnl_estimate=args.pnnl_estimate, 
        pnnl_fxrate=args.pnnl_fxrate,
    )

    global do_single, do_efficiency, do_rest
    do_single, do_efficiency, do_rest = args.do_single, args.do_efficiency, args.do_rest

    if not do_efficiency:
        parameter.efficiencies = np.ones(parameter.config_count, dtype=int)
    if not do_rest:
        parameter.rests_before_charge = np.zeros(parameter.config_count, dtype=int)
        parameter.rests_after_discharge = np.zeros(parameter.config_count, dtype=int)

    if do_single:
        net_arbitrage_revenue, variables = job(args.idx_config)

        # result saving
        output = np.hstack((
            np.array([
                parameter.capacities[args.idx_config],
                parameter.powers[args.idx_config],
                net_arbitrage_revenue,
                parameter.capexes[args.idx_config],
                parameter.opexes[args.idx_config],
            ])[:, None], 
            variables
        )) # (5, time_count + 1) # first column are params & ObjVal # s c d uc ud # soc final value removed

        save_output(timeseries, parameter, args, output, True) # disect_single_output(output) later

    else:
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            net_arbitrage_revenues = list(executor.map(job, range(parameter.config_count)))

        # result saving
        output = np.column_stack([
            np.arange(parameter.config_count),
            parameter.capacities,
            parameter.powers,
            np.array(net_arbitrage_revenues),
            parameter.capexes,
            parameter.opexes,
            parameter.efficiencies,
            parameter.rests_before_charge,
            parameter.rests_after_discharge
        ])

        save_output(timeseries, parameter, args, output, False)


if __name__ == "__main__":
    main()