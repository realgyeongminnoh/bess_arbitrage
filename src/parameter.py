import numpy as np
import pandas as pd

from src.timeseries import Timeseries


class Parameter:
    def __init__(
            self, 
            timeseries: Timeseries,
            parameter_pnnl: bool,
            pnnl_year: int, 
            pnnl_technology: str, 
            pnnl_estimate: str, 
            pnnl_fxrate: float,
    ):
        
        self.timeseries = timeseries
        self.parameter_pnnl = parameter_pnnl
        self.pnnl_year = pnnl_year
        self.pnnl_technology = pnnl_technology
        self.pnnl_estimate = pnnl_estimate
        self.pnnl_fxrate = pnnl_fxrate

        self.config_count: int = None
        self.capacities: np.ndarray = None
        self.powers: np.ndarray = None
        self.efficiencies: np.ndarray = None
        self.rests_before_charge: np.ndarray = None
        self.rests_after_discharge: np.ndarray = None
        self.capexes: np.ndarray = None
        self.opexes: np.ndarray = None

        if parameter_pnnl:
            self.get_pnnl(pnnl_year, pnnl_technology, pnnl_estimate, pnnl_fxrate)
        else:
            pass # TBD # CUSTOM


    def get_pnnl(self, pnnl_year: int, pnnl_technology: str, pnnl_estimate: str, pnnl_fxrate: float):
        bess_df = self._load_filtered_bess_df(pnnl_year, pnnl_technology, pnnl_estimate)
        self._get_parameter_arrays(bess_df)
        self._time_currency_adjustment(pnnl_fxrate)


    def _load_filtered_bess_df(self, year: int, tech: str, estimate: str) -> pd.DataFrame:
        bess_df = pd.read_excel(self.timeseries._dir_data_inputs / "ESGC_Cost_Performance_Database_v2024.xlsx", sheet_name="Database")

        # layer-1 filtering
        bess_df = bess_df[
            (bess_df["Year"] == year) & 
            (bess_df["Technology"] == tech.replace("_", " ").strip()) & 
            (bess_df["Estimate_type"] == estimate)
        ]

        # capacity column addition into the dataframe
        bess_df["Capacity_MWh"] = bess_df["Power_MW"] * bess_df["Duration_hr"]
        insert_at = bess_df.columns.get_loc("Duration_hr") + 1
        bess_df = bess_df[[*bess_df.columns[:insert_at], "Capacity_MWh", *bess_df.columns.drop(["Capacity_MWh"]).tolist()[insert_at:]]]

        # layer-2 filtering: max capacity: 1 GWh, max power <= max capacity
        bess_df = bess_df[
            (bess_df["Capacity_MWh"] <= 1000) # &
            # (bess_df["Power_MW"] <= bess_df["Capacity_MWh"])
        ].sort_values(by=["Capacity_MWh", "Power_MW"]).reset_index(drop=True)

        return bess_df


    def _get_parameter_arrays(self, bess_df: pd.DataFrame):
        pairs = (
            bess_df[["Capacity_MWh", "Power_MW"]]
            .drop_duplicates()
            .sort_values(["Capacity_MWh", "Power_MW"])
            .to_numpy(dtype=float)
        )
        capacities, powers = pairs[:, 0], pairs[:, 1]
        self.config_count = len(capacities)


        def _extract(parameter_name: str):
            return np.array([
                bess_df.query(
                    f"Capacity_MWh == {capacity} and Power_MW == {power} and Parameter == @parameter_name"
                )["Value"].values[0]
                for capacity, power in zip(capacities, powers)
            ], dtype=float)


        self.capacities = capacities * 1000
        self.powers = powers * 1000
        self.efficiencies = _extract("RTE (%)") ** 0.5
        self.rests_before_charge = _extract("Rest Before Charge (hrs)")
        self.rests_after_discharge = _extract("Rest After Discharge (hrs)")

        self.capexes = _extract("Total Installed Cost ($)")
        self.capexes -= (
            (_extract("EPC ($/kWh)") + _extract("Project Development ($/kWh)")) * self.capacities +
            _extract("Grid Integration ($/kW)") * self.powers
        )
        self.capexes *= 0.3
        self.opexes = _extract("Fixed O&M ($/kW-year)") * self.powers
        
    
    def _time_currency_adjustment(self, pnnl_fxrate: float):
        self.capexes *= pnnl_fxrate
        self.opexes *= (self.timeseries.hour_count / (365.25 * 24)) * pnnl_fxrate

        if self.timeseries.is_minute:
            self.capacities *= 60
            self.rests_before_charge = np.round(self.rests_before_charge * 60).astype(int)
            self.rests_after_discharge = np.round(self.rests_after_discharge * 60).astype(int)
        else:
            self.rests_before_charge = np.round(self.rests_before_charge).astype(int)
            self.rests_after_discharge = np.round(self.rests_after_discharge).astype(int)