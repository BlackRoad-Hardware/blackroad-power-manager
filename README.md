# blackroad-power-manager

> Power monitoring and management for edge devices — part of the BlackRoad Hardware platform.

## Features

- **Multi-Meter Support** — Main power, battery, solar, UPS meters per device
- **Real-Time Logging** — Voltage, current, wattage, and charge percentage tracking
- **Runtime Estimation** — Remaining battery life calculation from capacity and draw
- **Power Events** — charge_start, discharge, low_battery, shutdown, restore events
- **Auto Alerts** — Automatic low/critical battery event triggers at 20% and 5%
- **Budget Analysis** — Fleet-wide power budget check across multiple devices
- **Reports** — JSON power report export with historical statistics

## Quick Start

```bash
pip install -r requirements.txt
python power_manager.py report <device_id>
```

## Usage

```python
from power_manager import PowerManager

pm = PowerManager()

device = pm.register_device("edge-01", "Raspberry Pi", shutdown_threshold=3.0)
battery = pm.add_meter(device.id, "battery", capacity_wh=50.0)
solar = pm.add_meter(device.id, "solar")

pm.log_power(battery.id, voltage=12.0, current=1.5, charge_pct=80.0)
wattage = pm.calculate_wattage(battery.id)
runtime = pm.estimate_runtime(device.id)

budget = pm.power_budget_check([device.id])
report = pm.export_report(device.id, days=7)
```

## Power States

| State | Condition |
|-------|-----------|
| `normal` | Charge > 20% |
| `low` | Charge 5–20% |
| `critical` | Charge < 5% |
| `charging` | Solar meter or charge ≥ 95% |

## Testing

```bash
pytest --tb=short -v
```

## License

Proprietary — BlackRoad OS, Inc. All rights reserved.
