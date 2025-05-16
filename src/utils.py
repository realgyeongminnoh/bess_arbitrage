import csv
from pathlib import Path
import sys


def check_csv(configs):
    csv_path = Path(__file__).resolve().parents[1] / "data" / "outputs" / "historical" / "net_arbitrage_revenues.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        header = [
            "net_arbitrage_revenue",
            "day_start",
            "day_end",
            "power_output_rated",
            "energy_capacity_rated",
            "state_of_health",
            "state_of_charge_initial",
            "state_of_charge_minimum",
            "state_of_charge_maximum",
            "self_discharge_rate",
            "efficiency_charge",
            "efficiency_discharge",
            "rest_before_charge",
            "rest_after_discharge",
            "return_details",
        ]
        with csv_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
        return
    
    target_configs = ",".join([
        str(configs.day_start),
        str(configs.day_end),
        str(configs.power_output_rated),
        str(configs.energy_capacity_rated),
        str(configs.state_of_health),
        str(configs.state_of_charge_initial),
        str(configs.state_of_charge_minimum),
        str(configs.state_of_charge_maximum),
        str(configs.self_discharge_rate),
        str(configs.efficiency_charge),
        str(configs.efficiency_discharge),
        str(configs.rest_before_charge),
        str(configs.rest_after_discharge),
        str(configs.return_details),
    ])

    with csv_path.open("r") as f:
        next(f)
        existing_configs = {line.strip().split(",", 1)[1] for line in f}
    if target_configs in existing_configs:
        sys.exit(0)


def update_csv(output, configs):
    csv_path = Path(__file__).resolve().parents[1] / "data" / "outputs" / "historical" / "net_arbitrage_revenues.csv"

    row = [
        output,
        configs.day_start,
        configs.day_end,
        configs.power_output_rated,
        configs.energy_capacity_rated,
        configs.state_of_health,
        configs.state_of_charge_initial,
        configs.state_of_charge_minimum,
        configs.state_of_charge_maximum,
        configs.self_discharge_rate,
        configs.efficiency_charge,
        configs.efficiency_discharge,
        configs.rest_before_charge,
        configs.rest_after_discharge,
        configs.return_details,
    ]

    with csv_path.open("a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)