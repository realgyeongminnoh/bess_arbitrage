from pathlib import Path
import pickle
import numpy as np
import gurobipy as gp


def suppress_gurobi_parallel_spam():
    print(); (_ := gp.Model()).setParam("OutputFlag", 0)


def string_for_non_optimality(solver):

    def _to_yyyymmddhh(dt64):
        dt = str(dt64)[:13].replace("-", "").replace("T", "")
        return dt

    return f"""model status is not optimal for the inputs below
Timeseries
  is_minute      : {solver.timeseries.is_minute}
  is_historical  : {solver.timeseries.is_historical}
  end_exclude    : {solver.timeseries.end_exclude}
  time_start     : {_to_yyyymmddhh(solver.timeseries.time_start)}
  time_end       : {_to_yyyymmddhh(solver.timeseries.time_end)}
Parameter
  parameter_pnnl : {solver.parameter.parameter_pnnl}
  pnnl_technology: {solver.parameter.pnnl_technology}
  pnnl_year      : {solver.parameter.pnnl_year}
  pnnl_estimate  : {solver.parameter.pnnl_estimate}
  pnnl_fxrate    : {solver.parameter.pnnl_fxrate}
Solver
  do_single      : {solver.do_single}
  idx_config     : {solver.idx_config}
  do_efficiency  : {solver.do_efficiency}
  do_rest        : {solver.do_rest}
"""


def print_bess_config(parameter):
    print(" [*CONFIGS FROM PNNL*]")
    print(" [**FOR GIVEN SPECS**]")
    print(" [zero  MWh   MW   hr]")
    print(" [ idx  CAP  PWR  DUR]")
    print(np.hstack(( 
        np.arange(parameter.config_count, dtype=int)[:, None],
        (np.array(list(zip(parameter.capacities, parameter.powers))) / 1000).astype(int),
        (parameter.capacities / parameter.powers).astype(int)[:, None]
    )))


def generate_pnnl_output_dirs_filename(timeseries, parameter, do_efficiency, do_rest):
    # DIRECTORY
    root = Path(__file__).resolve().parents[1]
    dir_1 = "historical" if timeseries.is_historical else "forecasted"
    dir_2 = parameter.pnnl_technology

    out_dir = root / "data" / "outputs" / dir_1 / dir_2
    out_dir.mkdir(parents=True, exist_ok=True)

    # FOLRDER NAME
    def _to_yyyymmddhh(dt64):
        dt = str(dt64)[:13].replace("-", "").replace("T", "")
        return dt

    pnnl_year = {2023: "P", 2030: "F"}[parameter.pnnl_year]
    estimate_capitalletter = {"High": "H", "Point": "P", "Low": "L"}[parameter.pnnl_estimate]
    fxrate = parameter.pnnl_fxrate

    efficiency = "D" if do_efficiency else "N"
    rest = "D" if do_rest else "N"

    time_granurality = "M" if timeseries.is_minute else "H"
    time_start = _to_yyyymmddhh(timeseries.time_start)
    time_end = _to_yyyymmddhh(timeseries.time_end)
    
    filename = f"{pnnl_year}{estimate_capitalletter}{fxrate}_{efficiency}{rest}_{time_granurality}_{time_start}_{time_end}"
    return out_dir, filename # i literally cant do clean bc theres too many args code below is just enough for the project    


def save_single(solver):
    if solver.parameter.parameter_pnnl:
        out_dir, filename = generate_pnnl_output_dirs_filename(solver.timeseries, solver.parameter, solver.do_efficiency, solver.do_rest)
        with open(out_dir / f"S{solver.idx_config:02d}_{filename}.pickle", "wb") as f:
            pickle.dump(solver, f)


def save_multiple(timeseries, parameter, args, output: np.ndarray):
    if parameter.parameter_pnnl:
        out_dir, filename = generate_pnnl_output_dirs_filename(timeseries, parameter, args.do_efficiency, args.do_rest)
        np.save(out_dir / f"M{parameter.config_count:02d}_{filename}.npy", output)