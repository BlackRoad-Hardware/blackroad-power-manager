# blackroad-power-manager

[![CI](https://github.com/BlackRoad-Hardware/blackroad-power-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackRoad-Hardware/blackroad-power-manager/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue.svg)](https://www.python.org/)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-red.svg)](./LICENSE)

> **Production-grade** power monitoring and management for edge devices — part of the [BlackRoad Hardware](https://blackroad.io) platform.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Features](#2-features)
3. [Installation](#3-installation)
4. [Quick Start](#4-quick-start)
5. [Architecture](#5-architecture)
6. [API Reference](#6-api-reference)
   - [PowerManager](#61-powermanager)
   - [DeviceRecord](#62-devicerecord)
   - [PowerMeter](#63-powermeter)
   - [PowerReading](#64-powerreading)
   - [PowerEvent](#65-powerevent)
7. [Power States](#7-power-states)
8. [Event Types](#8-event-types)
9. [CLI Reference](#9-cli-reference)
10. [Configuration](#10-configuration)
11. [npm Integration](#11-npm-integration)
12. [Stripe Integration](#12-stripe-integration)
13. [End-to-End Testing](#13-end-to-end-testing)
14. [CI / CD](#14-ci--cd)
15. [Contributing](#15-contributing)
16. [Support](#16-support)
17. [License](#17-license)

---

## 1. Overview

`blackroad-power-manager` is the authoritative power telemetry service for the BlackRoad Hardware edge platform. It provides a persistent, SQLite-backed data store for multi-meter power readings, automatic alert events, fleet-wide budget analysis, and JSON report exports — all accessible from Python or the command line.

It is designed to run on resource-constrained edge hardware (Raspberry Pi, NVIDIA Jetson, custom SBCs) as well as in cloud back-end services that aggregate telemetry from distributed device fleets.

---

## 2. Features

| Feature | Description |
|---|---|
| **Multi-Meter Support** | `main`, `battery`, `solar`, and `ups` meter types per device |
| **Real-Time Logging** | Voltage, current, wattage, and charge percentage recorded with UTC timestamps |
| **Runtime Estimation** | Remaining battery life (hours) calculated from capacity and current draw |
| **Power Events** | `charge_start`, `discharge`, `low_battery`, `shutdown`, `restore` |
| **Auto Alerts** | Automatic event triggers at ≤ 20 % (low) and ≤ 5 % (critical) charge |
| **Budget Analysis** | Fleet-wide wattage and state summary across any set of device IDs |
| **JSON Reports** | Full power report export with per-meter statistics and recent events |
| **WAL SQLite** | Write-Ahead Logging for concurrent read performance |
| **Indexed Queries** | DB indexes on `(meter_id, timestamp)` and `(device_id, timestamp)` |

---

## 3. Installation

### Prerequisites

- Python 3.10 or later
- pip

### Install dependencies

```bash
pip install -r requirements.txt
```

### requirements.txt

```
pytest>=7.0
pytest-cov>=4.0
```

> The runtime library itself has **no third-party dependencies** — only the Python standard library is required in production.

---

## 4. Quick Start

```python
from power_manager import PowerManager

# Initialise (creates power_manager.db in the working directory)
pm = PowerManager()

# Register a device
device = pm.register_device("edge-01", "Raspberry Pi 4", shutdown_threshold=3.0)

# Attach meters
battery = pm.add_meter(device.id, "battery", capacity_wh=50.0, name="Main Battery")
solar   = pm.add_meter(device.id, "solar",   capacity_wh=0.0,  name="Solar Panel")

# Log a power reading
pm.log_power(battery.id, voltage=12.0, current=1.5, charge_pct=80.0)

# Derived values
wattage = pm.calculate_wattage(battery.id)       # → 18.0 W
runtime = pm.estimate_runtime(device.id)          # → hours remaining

# Fleet budget analysis
budget  = pm.power_budget_check([device.id])

# JSON report (last 7 days)
report  = pm.export_report(device.id, days=7)
print(report)
```

---

## 5. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     PowerManager                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │   Devices    │  │   Meters     │  │    Events     │ │
│  │  (register,  │  │  (add, log,  │  │ (trigger,     │ │
│  │   get)       │  │   history)   │  │  get_events)  │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘ │
│         │                 │                  │         │
│         └─────────────────┴──────────────────┘         │
│                           │                            │
│              ┌────────────▼────────────┐               │
│              │    SQLite (WAL mode)     │               │
│              │  devices                │               │
│              │  power_meters           │               │
│              │  power_readings         │               │
│              │  power_events           │               │
│              └─────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

The database file defaults to `power_manager.db` in the working directory. Pass a custom `Path` to `PowerManager(db_path=...)` to override.

---

## 6. API Reference

### 6.1 `PowerManager`

The main entry point for all power management operations.

```python
PowerManager(db_path: Path = Path("power_manager.db"))
```

#### Device methods

| Method | Signature | Returns | Description |
|---|---|---|---|
| `register_device` | `(device_id, name, shutdown_threshold=3.0, target_wh=None)` | `DeviceRecord` | Register or update a device |
| `get_device` | `(device_id)` | `DeviceRecord` | Retrieve a device; raises `ValueError` if not found |

#### Meter methods

| Method | Signature | Returns | Description |
|---|---|---|---|
| `add_meter` | `(device_id, meter_type, capacity_wh=0.0, name=None)` | `PowerMeter` | Add a meter to a device |
| `get_meter` | `(meter_id)` | `PowerMeter` | Retrieve a meter by ID |
| `list_meters` | `(device_id=None)` | `List[PowerMeter]` | List all meters, optionally filtered by device |

#### Telemetry methods

| Method | Signature | Returns | Description |
|---|---|---|---|
| `log_power` | `(meter_id, voltage, current, charge_pct=None)` | `PowerReading` | Record a power reading and update meter state |
| `calculate_wattage` | `(meter_id)` | `float` | Return current wattage (V × A) for a meter |
| `estimate_runtime` | `(device_id)` | `Optional[float]` | Estimate battery hours remaining; `None` if no battery |
| `get_history` | `(meter_id, hours=24)` | `List[PowerReading]` | Fetch readings from the last N hours |

#### Event methods

| Method | Signature | Returns | Description |
|---|---|---|---|
| `trigger_event` | `(device_id, event_type, value=0.0, note=None)` | `PowerEvent` | Manually fire a power event |
| `get_events` | `(device_id, limit=50)` | `List[PowerEvent]` | Retrieve recent events for a device |

#### Reporting methods

| Method | Signature | Returns | Description |
|---|---|---|---|
| `power_budget_check` | `(device_ids: List[str])` | `Dict[str, Any]` | Fleet-wide wattage and state summary |
| `export_report` | `(device_id, days=7)` | `str` (JSON) | Full JSON report with stats and events |

---

### 6.2 `DeviceRecord`

```python
@dataclass
class DeviceRecord:
    id: str
    name: str
    shutdown_threshold: float   # watts; default 3.0
    target_wh: Optional[float]  # optional energy budget
```

---

### 6.3 `PowerMeter`

```python
@dataclass
class PowerMeter:
    id: str
    device_id: str
    type: MeterType             # main | battery | solar | ups
    voltage: float
    current_draw: float
    capacity_wh: float
    charge_pct: float           # 0.0 – 100.0
    name: Optional[str]

    # Computed properties
    @property wattage() -> float        # voltage × current_draw
    @property state()   -> PowerState   # see §7
```

---

### 6.4 `PowerReading`

```python
@dataclass
class PowerReading:
    id: str
    meter_id: str
    voltage: float
    current_draw: float
    wattage: float
    charge_pct: float
    timestamp: str   # ISO 8601 UTC
```

---

### 6.5 `PowerEvent`

```python
@dataclass
class PowerEvent:
    id: str
    device_id: str
    type: PowerEventType   # see §8
    value: float
    timestamp: str         # ISO 8601 UTC
    note: Optional[str]
```

---

## 7. Power States

| State | `PowerState` value | Condition |
|---|---|---|
| Normal | `normal` | Battery charge > 20 % |
| Low | `low` | Battery charge 5 %–20 % |
| Critical | `critical` | Battery charge < 5 % |
| Charging | `charging` | Meter type is `solar`, or battery charge ≥ 95 % |
| Unknown | `unknown` | State cannot be determined |

---

## 8. Event Types

| Event | `PowerEventType` value | Triggered by |
|---|---|---|
| Charge start | `charge_start` | Manual / integration call |
| Discharge | `discharge` | `log_power` when charge ≤ 20 % (initial warning) |
| Low battery | `low_battery` | `log_power` when charge ≤ 5 % (critical alert) |
| Shutdown | `shutdown` | Manual / integration call |
| Restore | `restore` | Manual / integration call |

Auto-triggered events are fired inside `log_power` for `battery` meter types only.
When charge falls into the critical range (≤ 5 %), `low_battery` is fired exclusively; the `discharge` warning is only raised for the 5 %–20 % range.

---

## 9. CLI Reference

```bash
python power_manager.py report <device_id> [--days N]
```

| Argument | Default | Description |
|---|---|---|
| `device_id` | *(required)* | Device ID to report on |
| `--days N` | `7` | Number of days of history to include |

**Example**

```bash
python power_manager.py report edge-01 --days 14
```

Output is a pretty-printed JSON power report written to stdout.

---

## 10. Configuration

| Variable / Parameter | Default | Description |
|---|---|---|
| `db_path` | `power_manager.db` | SQLite database file path (passed to `PowerManager`) |
| `LOW_BATTERY_THRESHOLD` | `20.0` % | Charge level that triggers a `discharge` event |
| `CRITICAL_BATTERY_THRESHOLD` | `5.0` % | Charge level that triggers a `low_battery` event |
| `shutdown_threshold` | `3.0` W | Per-device shutdown wattage threshold |

All thresholds are defined as module-level constants in `power_manager.py` and can be overridden per device via `register_device`.

---

## 11. npm Integration

`blackroad-power-manager` is part of the **BlackRoad Hardware** full-stack platform. The Python library exposes its data over a REST or WebSocket service layer that is consumed by the BlackRoad JavaScript / TypeScript SDK:

```bash
npm install @blackroad/power-client
```

```typescript
import { PowerClient } from "@blackroad/power-client";

const client = new PowerClient({ baseUrl: "http://your-edge-host:8080" });

const budget = await client.getBudget(["edge-01", "edge-02"]);
const report = await client.getReport("edge-01", { days: 7 });
```

The npm package provides:
- Fully typed request/response models mirroring the Python dataclasses
- Real-time event streaming via WebSocket
- Stripe-compatible usage record helpers (see §12)
- React hooks for live power dashboards

> **Note:** `@blackroad/power-client` is published to the public npm registry under the BlackRoad Hardware organisation scope.

---

## 12. Stripe Integration

Power consumption data can be fed directly into **Stripe Billing** to create usage-based billing records for fleet operators.

### Metered billing flow

```python
import json, os, time
import stripe
from power_manager import PowerManager

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

pm = PowerManager()
report_json = pm.export_report("edge-01", days=30)
report = json.loads(report_json)

# Sum total watt-hours consumed across all meters in the report period
total_wh = sum(
    m["avg_wattage"] * 24 * report["period_days"]
    for m in report["meters"]
    if "avg_wattage" in m
)

# Record usage against a Stripe subscription item
stripe.UsageRecord.create(
    subscription_item="si_XXXXXXXXXXXX",    # subscription item ID
    quantity=int(total_wh),                 # watt-hours as the billable unit
    timestamp=int(time.time()),
    action="set",
)
```

### Stripe configuration checklist

- [ ] Create a **metered price** in the Stripe Dashboard with unit = `watt-hour`
- [ ] Attach the price to a subscription item for each fleet customer
- [ ] Store `subscription_item_id` alongside each `DeviceRecord`
- [ ] Call `create_usage_record` on a scheduled job (daily or monthly)
- [ ] Use Stripe webhooks to handle `invoice.payment_failed` → trigger `shutdown` event

> Store `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` as environment variables — never commit secrets to source control.

---

## 13. End-to-End Testing

The test suite uses **pytest** and exercises the full stack from `PowerManager` initialisation through DB writes, event auto-triggers, budget checks, and report exports.

### Run all tests

```bash
pytest --tb=short -v
```

### Run with coverage

```bash
pytest --tb=short --cov=. --cov-report=term-missing -v
```

### Run against a specific Python version

```bash
python3.12 -m pytest --tb=short -v
```

### Key E2E scenarios covered

| Test | What it validates |
|---|---|
| `test_register_device` | Device creation and defaults |
| `test_log_power` | Reading persistence and wattage calculation |
| `test_log_power_clamps_charge` | Charge % clamped to `[0, 100]` |
| `test_estimate_runtime` | Runtime hours derived from capacity and draw |
| `test_low_battery_auto_event` | Auto `discharge` event at ≤ 20 % |
| `test_critical_battery_auto_event` | Auto `low_battery` event at ≤ 5 % |
| `test_power_budget_check` | Fleet-wide budget aggregation |
| `test_power_budget_unknown_device` | Error handling for missing devices |
| `test_power_state_*` | All `PowerState` transitions |
| `test_solar_state_always_charging` | Solar meter always returns `charging` |
| `test_get_history` | Time-window filtering on readings |
| `test_export_report` | Full JSON report structure and content |

### Fixture overview

| Fixture | Scope | Description |
|---|---|---|
| `pm` | function | Fresh `PowerManager` backed by a `tmp_path` database |
| `device` | function | Pre-registered `DeviceRecord` (`dev-001`, `Edge Node`) |
| `battery_meter` | function | 50 Wh battery meter on `device` |
| `solar_meter` | function | Solar meter on `device` |

---

## 14. CI / CD

Tests are executed automatically on every push and pull request to `main` via GitHub Actions across the full Python matrix:

| Python version | Status |
|---|---|
| 3.10 | [![CI](https://github.com/BlackRoad-Hardware/blackroad-power-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackRoad-Hardware/blackroad-power-manager/actions/workflows/ci.yml) |
| 3.11 | [![CI](https://github.com/BlackRoad-Hardware/blackroad-power-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackRoad-Hardware/blackroad-power-manager/actions/workflows/ci.yml) |
| 3.12 | [![CI](https://github.com/BlackRoad-Hardware/blackroad-power-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackRoad-Hardware/blackroad-power-manager/actions/workflows/ci.yml) |

Workflow file: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

---

## 15. Contributing

1. Fork the repository and create a feature branch from `main`.
2. Write or update tests to cover your changes.
3. Run the full test suite locally: `pytest --tb=short -v`.
4. Open a pull request against `main` with a clear description of the change and its motivation.
5. All CI checks must pass before a review is requested.

**Code style:** follow PEP 8. Use type annotations for all public methods.

---

## 16. Support

For support, licensing enquiries, or enterprise fleet integration questions, contact the BlackRoad Hardware team:

- **Email:** support@blackroad.io
- **Platform:** [https://blackroad.io](https://blackroad.io)

---

## 17. License

Proprietary — BlackRoad OS, Inc. All rights reserved.  
See [LICENSE](./LICENSE) for full terms.
