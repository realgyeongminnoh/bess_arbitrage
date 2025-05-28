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
    # time-related
    parser.add_argument("--date_start_int", "--dsi", type=int, required=True)
    parser.add_argument("--date_end_int", "--dei", type=int, required=True)
    parser.add_argument("--time_horizon_idx_smp", "--thn_smp", type=int, required=True)
    parser.add_argument("--time_horizon_idx_smp_ref", "--thn_smp_ref", type=int, default=0)
    # solver bool flags
    parser.add_argument("--use_smp_ref", "--usr", action="store_true")
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

    time_start, time_end = convert_date_int_to_datetime64(args.date_start_int, False), convert_date_int_to_datetime64(args.date_end_int, True)

    output = optimize(
        parameter=parameter, 
        smp=get_smp(args.time_horizon_idx_smp, time_start, time_end),
        smp_ref=get_smp(args.time_horizon_idx_smp_ref, time_start, time_end) if args.use_smp_ref else None,
        return_detail=args.return_detail,
    )

    save_custom_output(time_start, time_end, args, output)


if __name__=="__main__":
    main()