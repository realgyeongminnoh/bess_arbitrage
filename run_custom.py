import argparse

from src.parameter import Parameter
from src.operation_optimization import optimize
from src.utils import convert_date_int_to_datetime64, get_smp, save_custom_output


def parse_args():
    parser = argparse.ArgumentParser()
    # parameter
    parser.add_argument("--ecr", type=int, required=True)
    parser.add_argument("--por", type=int, required=True)
    parser.add_argument("--soh", type=float, default=1)
    parser.add_argument("--soc_ini", type=float, default=0)
    parser.add_argument("--soc_min", type=float, default=0)
    parser.add_argument("--soc_max", type=float, default=1)
    parser.add_argument("--sdr", type=float, default=0)
    parser.add_argument("--ec", type=float, default=1)
    parser.add_argument("--ed", type=float, default=1)
    parser.add_argument("--rbc", type=int, default=0)
    parser.add_argument("--rad", type=int, default=0)
    # time horizon and dataset related
    parser.add_argument("--time_horizon_date_start", "--thds", type=int, required=True)
    parser.add_argument("--time_horizon_date_end", "--thde", type=int, required=True)
    parser.add_argument("--dataset_idx_opt", "--dio", type=int, required=True)
    parser.add_argument("--dataset_idx_rev", "--dir", type=int, required=True)
    # solver bool flags
    parser.add_argument("--return_detail", "--rd", action="store_true")

    return parser.parse_args()


def main():
    args = parse_args()

    parameter = Parameter(
        ecr=args.ecr,
        por=args.por,
        soh=args.soh,
        soc_ini=args.soc_ini,
        soc_min=args.soc_min,
        soc_max=args.soc_max,
        sdr=args.sdr,
        ec=args.ec,
        ed=args.ed,
        rbc=args.rbc,
        rad=args.rad,
    )

    time_horizon_start = convert_date_int_to_datetime64(args.time_horizon_date_start, False)
    time_horizon_end = convert_date_int_to_datetime64(args.time_horizon_date_end, True)

    output = optimize(
        parameter=parameter, 
        smp_opt=get_smp(args.dataset_idx_opt, time_horizon_start, time_horizon_end),
        smp_rev=get_smp(args.dataset_idx_rev, time_horizon_start, time_horizon_end) if (args.dataset_idx_rev == args.dataset_idx_opt) else None,
        return_detail=args.return_detail,
    )

    save_custom_output(time_horizon_start, time_horizon_end, args, output)


if __name__=="__main__":
    main()