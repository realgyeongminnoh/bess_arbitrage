import numpy as np
import pandas as pd
from pathlib import Path

class Pnnl:
    def __init__(
        self,
        original_df: pd.DataFrame,
        technology: str,
        year: int,
        estimate: str,
        fxrate: int,
    ):
        self.technology = technology
        self.year = year
        self.estimate = estimate
        self.fxrate = fxrate

        self.count_configs: int = None
        self.configs: np.ndarray = None

        self.get_pnnl(original_df)
        self._save_configs_csv()


    def get_pnnl(self, original_df):
        df = self.filter_original_df(original_df)
        self._organize(df)


    def filter_original_df(self, original_df) -> pd.DataFrame:
        df = original_df[
            (original_df.Technology == self.technology.replace("_", " ").strip()) &
            (original_df.Year == self.year) &
            (original_df.Estimate_type == self.estimate)
        ].sort_values(by=["Capacity_MWh", "Power_MW"]).reset_index(drop=True)

        return df
    

    def _organize(self, df: pd.DataFrame) -> np.ndarray:
        pairs = (
            df[["Capacity_MWh", "Power_MW"]]
            .drop_duplicates()
            .sort_values(["Capacity_MWh", "Power_MW"])
            .to_numpy(dtype=int)
        )
        self.count_configs = len(pairs)
        configs = np.empty((self.count_configs, 8))
        configs[:, [0, 1]] = pairs # energy capacity rated, power output rated

        def _extract(parameter_name: str):
            return np.array([
                df.query(
                    f"Capacity_MWh == {capacity} and Power_MW == {power} and Parameter == @parameter_name"
                )["Value"].values[0]
                for capacity, power in pairs
            ], dtype=float)

        # Peformance Params###################################################################################
        depths_of_charge= _extract("Primary DOD (%)") # DOD for socmin and socamx
        configs[:, 2] = np.round((1 - depths_of_charge) / 2, decimals=2) # SOCMIN # rounding for the FPE n saving csv
        configs[:, 3] = np.round((1 + depths_of_charge) / 2, decimals=2) # SOCMAX

        configs[:, 4] = _extract("RTE (%)") ** 0.5 # efficiencies
        configs[:, 5] = np.floor(_extract("Rest Before Charge (hrs)")) # rests # floored

        configs[:, :2] *= 1000 # M -> k
        
        # Costs info#########################################################################################
        capexes = _extract("Total Installed Cost ($)") * self.fxrate
        # CAPEX DECOMPOSITION EXCLUDED # FULL CAPEX
        # capexes -= (
        #     (_extract("EPC ($/kWh)") + _extract("Project Development ($/kWh)")) * configs[:, 0] +
        #     _extract("Grid Integration ($/kW)") * configs[:, 1]
        # )
        opexes_yearly = _extract("Fixed O&M ($/kW-year)") * configs[:, 1] * self.fxrate # YEARLY OPEX

        configs[:, 6] = opexes_yearly.astype(int)
        configs[:, 7] = capexes.astype(int)

        # just checking
        if not np.all(_extract("Rest Before Charge (hrs)") == _extract("Rest After Discharge (hrs)")):
            raise ValueError("RBC != RAD FOUND")

        self.configs = configs


    def _save_configs_csv(self):
        path_csv = Path(__file__).resolve().parents[0] / "data" / "inputs" / "pnnl"
        path_csv.mkdir(parents=True, exist_ok=True)

        file_name = f"{self.technology}_{self.year}_{self.estimate}.csv"

        # np.savetxt(
        #     path_csv / file_name, self.configs, delimiter=",", comments="",
        #     header="energy_capacity_rated,power_output_rated,state_of_charge_minimum,state_of_charge_maximum,efficiency,rest,opex_yearly,capex",
        # )

        header = [
            "energy_capacity_rated",
            "power_output_rated",
            "state_of_charge_minimum",
            "state_of_charge_maximum",
            "efficiency",
            "rest",
            "opex_yearly",
            "capex"
        ]

        df = pd.DataFrame(self.configs, columns=header)
        df = df.astype({
            "energy_capacity_rated": "int64",
            "power_output_rated": "int64",
            "rest": "int64",
            "opex_yearly": "int64",
            "capex": "int64"
        })
        df.to_csv(path_csv / file_name, index=False)


def lighter_original_df(df: pd.DataFrame) -> pd.DataFrame:
    df["Capacity_MWh"] = df.Power_MW * df.Duration_hr
    insert_at = df.columns.get_loc("Duration_hr") + 1
    df = df[[*df.columns[:insert_at], "Capacity_MWh", *df.columns.drop(["Capacity_MWh"]).tolist()[insert_at:]]]
    df = df[(df["Capacity_MWh"] <= 1000)]
    return df


def main():
    original_df = pd.read_excel(Path(__file__).resolve().parents[0] / "data" / "inputs" / "pnnl" / "ESGC_Cost_Performance_Database_v2024.xlsx", sheet_name="Database")
    original_df = lighter_original_df(original_df)

    technology_all = ["Lithium-ion_LFP", "Lithium-ion_NMC", "Lead_Acid", "Vanadium_Redox_Flow", "Zinc"]
    estimate_all = ["Point", "High", "Low"]
    year_all = [2023, 2030]

    count = 0
    for technology in technology_all:
        for estimate in estimate_all:
            for year in year_all:

                Pnnl(
                    original_df=original_df,
                    technology=technology,
                    year=year,
                    estimate=estimate,
                    fxrate=1333,
                )

                count += 1

    print(f"{count} csvs about BESS configs based on PNNL dataset are saved")


if __name__=="__main__":
    main()