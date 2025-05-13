import os
import argparse
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from time import perf_counter as timer

from src import *
from src.utils import *


def parse_args():
    parser = argparse.ArgumentParser()
    # timeseries args
    parser.add_argument("--is_minute", "--im", action="store_true", help="minute-level optimization granurality, otherwise hour-level")
    parser.add_argument("--is_historical", "--ih", action="store_true")
    parser.add_argument("--end_exclude", "--ee", action="store_true", help="time_end provided by --et is excluded")
    parser.add_argument("--time_start", "--st", type=int, required=True, help="yyyymmddhh")
    parser.add_argument("--time_end", "--et", type=int, required=True, help="yyyymmddhh")
    # parameter args
    parser.add_argument("--parameter_pnnl", "--pp", action="store_true", help="use parameter from PNNL database")
    parser.add_argument("--pnnl_year", "--py", type=int, required=False, default=2023, help="(default=2023)")
    parser.add_argument("--pnnl_technology", "--pt", type=str, required=False, default="Lithium-ion_LFP", help="(default=Lithium-ion_LFP)")
    parser.add_argument("--pnnl_estimate", "--pe", type=str, required=False, default="Point", help="(dfeault=Point)")
    parser.add_argument("--pnnl_fxrate", "--fx", type=float, required=False, default=1333, help="FX rate of USDKRW as PNNL is in USD; (default=1333)")
    # solver args
    parser.add_argument("--solver_model", "--sm", type=int, required=False, default=0, help="(default=0)")


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
        pass # TBD # FORECASTED

    # parameter args
    if args.parameter_pnnl:
        # TBD # PNNL ARGS VALIDATION FOR THESE MUST MOVE INSIDE INTO PARAMETER CLASS
        # if None in (args.pnnl_year, args.pnnl_technology, args.pnnl_estimate):
        #     raise ValueError("Using pnnl dataset rqeuires arguments of --py --pt --pe")
        if not (1100 <= args.pnnl_fxrate <= 1500):
            raise ValueError("FX rate of USDKRW is not sensible")
    else:
        pass # TBD # CUSTOM

    # solver args
    if args.solver_model not in [0, 1, 2]:
        raise ValueError("solver model number out of valid range")


def job(idx_config):
    solver = Solver(
        timeseries,
        parameter, 
        solver_model=solver_model, 
        idx_config=idx_config
    )

    return solver.solve()


def main():
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
        pnnl_year=args.pnnl_year, 
        pnnl_technology=args.pnnl_technology,
        pnnl_estimate=args.pnnl_estimate, 
        pnnl_fxrate=args.pnnl_fxrate,
    )

    suppress_gurobi_parallel_spam()

    global solver_model
    solver_model = args.solver_model

    # if solver_model == 2:
    #     net_arbitrage_revenues = []
    #     for idx_config in range(parameter.config_count):
    #         net_arbitrage_revenues.append(job(idx_config))
    # else:
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        net_arbitrage_revenues = list(executor.map(job, range(parameter.config_count)))

    net_arbitrage_revenues = np.array(net_arbitrage_revenues)
        
    output = np.column_stack([
        parameter.capacities,
        parameter.powers,
        net_arbitrage_revenues,
        parameter.capexes,
        parameter.opexes,
        parameter.efficiencies,
        parameter.rests_before_charge,
        parameter.rests_after_discharge
    ])

    save_output(timeseries, args.pnnl_technology, solver_model, output)


if __name__ == "__main__":
    main()