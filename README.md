<!-- BlackRoad SEO Enhanced -->

# ulackroad power manager

> Part of **[BlackRoad OS](https://blackroad.io)** — Sovereign Computing for Everyone

[![BlackRoad OS](https://img.shields.io/badge/BlackRoad-OS-ff1d6c?style=for-the-badge)](https://blackroad.io)
[![BlackRoad Hardware](https://img.shields.io/badge/Org-BlackRoad-Hardware-2979ff?style=for-the-badge)](https://github.com/BlackRoad-Hardware)
[![License](https://img.shields.io/badge/License-Proprietary-f5a623?style=for-the-badge)](LICENSE)

**ulackroad power manager** is part of the **BlackRoad OS** ecosystem — a sovereign, distributed operating system built on edge computing, local AI, and mesh networking by **BlackRoad OS, Inc.**

## About BlackRoad OS

BlackRoad OS is a sovereign computing platform that runs AI locally on your own hardware. No cloud dependencies. No API keys. No surveillance. Built by [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc), a Delaware C-Corp founded in 2025.

### Key Features
- **Local AI** — Run LLMs on Raspberry Pi, Hailo-8, and commodity hardware
- **Mesh Networking** — WireGuard VPN, NATS pub/sub, peer-to-peer communication
- **Edge Computing** — 52 TOPS of AI acceleration across a Pi fleet
- **Self-Hosted Everything** — Git, DNS, storage, CI/CD, chat — all sovereign
- **Zero Cloud Dependencies** — Your data stays on your hardware

### The BlackRoad Ecosystem
| Organization | Focus |
|---|---|
| [BlackRoad OS](https://github.com/BlackRoad-OS) | Core platform and applications |
| [BlackRoad OS, Inc.](https://github.com/BlackRoad-OS-Inc) | Corporate and enterprise |
| [BlackRoad AI](https://github.com/BlackRoad-AI) | Artificial intelligence and ML |
| [BlackRoad Hardware](https://github.com/BlackRoad-Hardware) | Edge hardware and IoT |
| [BlackRoad Security](https://github.com/BlackRoad-Security) | Cybersecurity and auditing |
| [BlackRoad Quantum](https://github.com/BlackRoad-Quantum) | Quantum computing research |
| [BlackRoad Agents](https://github.com/BlackRoad-Agents) | Autonomous AI agents |
| [BlackRoad Network](https://github.com/BlackRoad-Network) | Mesh and distributed networking |
| [BlackRoad Education](https://github.com/BlackRoad-Education) | Learning and tutoring platforms |
| [BlackRoad Labs](https://github.com/BlackRoad-Labs) | Research and experiments |
| [BlackRoad Cloud](https://github.com/BlackRoad-Cloud) | Self-hosted cloud infrastructure |
| [BlackRoad Forge](https://github.com/BlackRoad-Forge) | Developer tools and utilities |

### Links
- **Website**: [blackroad.io](https://blackroad.io)
- **Documentation**: [docs.blackroad.io](https://docs.blackroad.io)
- **Chat**: [chat.blackroad.io](https://chat.blackroad.io)
- **Search**: [search.blackroad.io](https://search.blackroad.io)

---


> Power monitoring and management for edge devices

Part of the [BlackRoad OS](https://blackroad.io) ecosystem — [BlackRoad-Hardware](https://github.com/BlackRoad-Hardware)

---

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
