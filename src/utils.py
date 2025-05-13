from pathlib import Path
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
  pnnl_year      : {solver.parameter.pnnl_year}
  pnnl_technology: {solver.parameter.pnnl_technology}
  pnnl_estimate  : {solver.parameter.pnnl_estimate}
  pnnl_fxrate    : {solver.parameter.pnnl_fxrate}
Solver
  idx_config     : {solver.idx_config}
  do_efficiency  : {solver.do_efficiency}
  do_rest        : {solver.do_rest}
  return_model   : {solver.return_model}
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


def save_output(timeseries, pnnl_Technology: str, solver_model: int, output: np.ndarray):
    root = Path(__file__).resolve().parents[1]
    folder = "historical" if timeseries.is_historical else "forecasted"

    out_dir = root / "data" / "outputs" / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = "minute" if timeseries.is_minute else "hour"

    def _to_yyyymmddhh(dt64):
        dt = str(dt64)[:13].replace("-", "").replace("T", "")
        return dt

    filename = f"{pnnl_Technology}_{mode}_model_{solver_model}_{_to_yyyymmddhh(timeseries.time_start)}_{_to_yyyymmddhh(timeseries.time_end)}.npy"

    np.save(out_dir / filename, output)