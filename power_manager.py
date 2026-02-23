"""
BlackRoad Power Manager - Power monitoring and management for edge devices.
"""
from __future__ import annotations
import json, logging, sqlite3, uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
DB_PATH = Path("power_manager.db")

class MeterType(str, Enum):
    MAIN = "main"; BATTERY = "battery"; SOLAR = "solar"; UPS = "ups"

class PowerEventType(str, Enum):
    CHARGE_START = "charge_start"; DISCHARGE = "discharge"
    LOW_BATTERY = "low_battery"; SHUTDOWN = "shutdown"; RESTORE = "restore"

class PowerState(str, Enum):
    NORMAL = "normal"; LOW = "low"; CRITICAL = "critical"; CHARGING = "charging"; UNKNOWN = "unknown"

LOW_BATTERY_THRESHOLD = 20.0   # percent
CRITICAL_BATTERY_THRESHOLD = 5.0

@dataclass
class PowerMeter:
    id: str; device_id: str; type: MeterType; voltage: float; current_draw: float
    capacity_wh: float; charge_pct: float; name: Optional[str] = None

    @property
    def wattage(self) -> float:
        return round(self.voltage * self.current_draw, 4)

    @property
    def state(self) -> PowerState:
        if self.type == MeterType.SOLAR: return PowerState.CHARGING
        if self.charge_pct <= CRITICAL_BATTERY_THRESHOLD: return PowerState.CRITICAL
        if self.charge_pct <= LOW_BATTERY_THRESHOLD: return PowerState.LOW
        if self.charge_pct >= 95.0: return PowerState.CHARGING
        return PowerState.NORMAL

    @classmethod
    def from_row(cls, row) -> "PowerMeter":
        return cls(id=row["id"], device_id=row["device_id"],
                   type=MeterType(row["type"]), voltage=row["voltage"],
                   current_draw=row["current_draw"], capacity_wh=row["capacity_wh"],
                   charge_pct=row["charge_pct"], name=row["name"])

@dataclass
class PowerReading:
    id: str; meter_id: str; voltage: float; current_draw: float
    wattage: float; charge_pct: float; timestamp: str

    @classmethod
    def from_row(cls, row) -> "PowerReading":
        return cls(id=row["id"], meter_id=row["meter_id"], voltage=row["voltage"],
                   current_draw=row["current_draw"], wattage=row["wattage"],
                   charge_pct=row["charge_pct"], timestamp=row["timestamp"])

@dataclass
class PowerEvent:
    id: str; device_id: str; type: PowerEventType; value: float; timestamp: str; note: Optional[str]

    @classmethod
    def from_row(cls, row) -> "PowerEvent":
        return cls(id=row["id"], device_id=row["device_id"],
                   type=PowerEventType(row["type"]), value=row["value"],
                   timestamp=row["timestamp"], note=row["note"])

@dataclass
class DeviceRecord:
    id: str; name: str; shutdown_threshold: float = 3.0; target_wh: Optional[float] = None

    @classmethod
    def from_row(cls, row) -> "DeviceRecord":
        return cls(id=row["id"], name=row["name"],
                   shutdown_threshold=row["shutdown_threshold"],
                   target_wh=row["target_wh"])

@contextmanager
def db_conn(db_path: Path = DB_PATH):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn; conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def init_db(db_path: Path = DB_PATH) -> None:
    with db_conn(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY, name TEXT NOT NULL,
                shutdown_threshold REAL NOT NULL DEFAULT 3.0, target_wh REAL
            );
            CREATE TABLE IF NOT EXISTS power_meters (
                id TEXT PRIMARY KEY, device_id TEXT NOT NULL, type TEXT NOT NULL,
                voltage REAL NOT NULL DEFAULT 0.0, current_draw REAL NOT NULL DEFAULT 0.0,
                capacity_wh REAL NOT NULL DEFAULT 0.0, charge_pct REAL NOT NULL DEFAULT 100.0,
                name TEXT, FOREIGN KEY (device_id) REFERENCES devices(id)
            );
            CREATE TABLE IF NOT EXISTS power_readings (
                id TEXT PRIMARY KEY, meter_id TEXT NOT NULL,
                voltage REAL NOT NULL, current_draw REAL NOT NULL,
                wattage REAL NOT NULL, charge_pct REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (meter_id) REFERENCES power_meters(id)
            );
            CREATE TABLE IF NOT EXISTS power_events (
                id TEXT PRIMARY KEY, device_id TEXT NOT NULL,
                type TEXT NOT NULL, value REAL NOT NULL DEFAULT 0.0,
                timestamp TEXT NOT NULL, note TEXT,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            );
            CREATE INDEX IF NOT EXISTS idx_readings_meter ON power_readings(meter_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_device ON power_events(device_id, timestamp);
        """)
    logger.info("Power manager DB initialised at %s", db_path)

class PowerManager:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path; init_db(db_path)

    # -- Device & Meter setup --
    def register_device(self, device_id: str, name: str,
                         shutdown_threshold: float = 3.0,
                         target_wh: Optional[float] = None) -> DeviceRecord:
        with db_conn(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO devices (id,name,shutdown_threshold,target_wh) "
                "VALUES (?,?,?,?)", (device_id, name, shutdown_threshold, target_wh))
        return self.get_device(device_id)

    def get_device(self, device_id: str) -> DeviceRecord:
        with db_conn(self.db_path) as conn:
            row = conn.execute("SELECT * FROM devices WHERE id=?", (device_id,)).fetchone()
        if not row: raise ValueError(f"Device not found: {device_id}")
        return DeviceRecord.from_row(row)

    def add_meter(self, device_id: str, meter_type: str, capacity_wh: float = 0.0,
                   name: Optional[str] = None) -> PowerMeter:
        self.get_device(device_id)
        meter_id = str(uuid.uuid4())
        with db_conn(self.db_path) as conn:
            conn.execute(
                "INSERT INTO power_meters (id,device_id,type,capacity_wh,name) VALUES (?,?,?,?,?)",
                (meter_id, device_id, MeterType(meter_type).value, capacity_wh, name))
        return self.get_meter(meter_id)

    def get_meter(self, meter_id: str) -> PowerMeter:
        with db_conn(self.db_path) as conn:
            row = conn.execute("SELECT * FROM power_meters WHERE id=?", (meter_id,)).fetchone()
        if not row: raise ValueError(f"Meter not found: {meter_id}")
        return PowerMeter.from_row(row)

    def list_meters(self, device_id: Optional[str] = None) -> List[PowerMeter]:
        q = "SELECT * FROM power_meters WHERE 1=1"; params: List[Any] = []
        if device_id: q += " AND device_id=?"; params.append(device_id)
        with db_conn(self.db_path) as conn:
            rows = conn.execute(q, params).fetchall()
        return [PowerMeter.from_row(r) for r in rows]

    # -- Core operations --
    def log_power(self, meter_id: str, voltage: float, current: float,
                   charge_pct: Optional[float] = None) -> PowerReading:
        meter = self.get_meter(meter_id)
        wattage = round(voltage * current, 4)
        pct = charge_pct if charge_pct is not None else meter.charge_pct
        pct = max(0.0, min(100.0, pct))
        now = datetime.now(timezone.utc).isoformat()
        rid = str(uuid.uuid4())
        with db_conn(self.db_path) as conn:
            conn.execute(
                "INSERT INTO power_readings (id,meter_id,voltage,current_draw,wattage,charge_pct,timestamp) "
                "VALUES (?,?,?,?,?,?,?)", (rid, meter_id, voltage, current, wattage, pct, now))
            conn.execute(
                "UPDATE power_meters SET voltage=?, current_draw=?, charge_pct=? WHERE id=?",
                (voltage, current, pct, meter_id))
        # Auto-trigger low battery events
        if meter.type == MeterType.BATTERY:
            if pct <= CRITICAL_BATTERY_THRESHOLD:
                self.trigger_event(meter.device_id, "low_battery", pct)
            elif pct <= LOW_BATTERY_THRESHOLD:
                self.trigger_event(meter.device_id, "discharge", pct)
        return PowerReading(id=rid, meter_id=meter_id, voltage=voltage,
                             current_draw=current, wattage=wattage, charge_pct=pct, timestamp=now)

    def calculate_wattage(self, meter_id: str) -> float:
        meter = self.get_meter(meter_id)
        return meter.wattage

    def estimate_runtime(self, device_id: str) -> Optional[float]:
        """Estimate remaining runtime in hours based on battery charge and draw."""
        meters = self.list_meters(device_id)
        battery_meters = [m for m in meters if m.type == MeterType.BATTERY and m.current_draw > 0]
        if not battery_meters: return None
        bm = battery_meters[0]
        remaining_wh = bm.capacity_wh * (bm.charge_pct / 100.0)
        if bm.wattage <= 0: return None
        hours = remaining_wh / bm.wattage
        return round(hours, 2)

    def trigger_event(self, device_id: str, event_type: str, value: float = 0.0,
                       note: Optional[str] = None) -> PowerEvent:
        self.get_device(device_id)
        eid = str(uuid.uuid4()); now = datetime.now(timezone.utc).isoformat()
        etype = PowerEventType(event_type)
        with db_conn(self.db_path) as conn:
            conn.execute(
                "INSERT INTO power_events (id,device_id,type,value,timestamp,note) "
                "VALUES (?,?,?,?,?,?)", (eid, device_id, etype.value, value, now, note))
        logger.info("Power event %s for device %s value=%.2f", event_type, device_id, value)
        return PowerEvent(id=eid, device_id=device_id, type=etype,
                          value=value, timestamp=now, note=note)

    def get_events(self, device_id: str, limit: int = 50) -> List[PowerEvent]:
        with db_conn(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM power_events WHERE device_id=? ORDER BY timestamp DESC LIMIT ?",
                (device_id, limit)).fetchall()
        return [PowerEvent.from_row(r) for r in rows]

    def power_budget_check(self, device_ids: List[str]) -> Dict[str, Any]:
        """Check power budget across multiple devices."""
        results = {}
        for dev_id in device_ids:
            try:
                self.get_device(dev_id)  # validates existence
                meters = self.list_meters(dev_id)
                total_wattage = sum(m.wattage for m in meters)
                battery_meters = [m for m in meters if m.type == MeterType.BATTERY]
                solar_meters = [m for m in meters if m.type == MeterType.SOLAR]
                runtime = self.estimate_runtime(dev_id)
                results[dev_id] = {
                    "total_wattage": round(total_wattage, 4),
                    "battery_count": len(battery_meters),
                    "solar_count": len(solar_meters),
                    "avg_charge_pct": round(
                        sum(m.charge_pct for m in battery_meters) / len(battery_meters), 2
                    ) if battery_meters else None,
                    "estimated_runtime_hours": runtime,
                    "states": [m.state.value for m in meters],
                }
            except (ValueError, Exception) as exc:
                results[dev_id] = {"error": str(exc)}
        return results

    def get_history(self, meter_id: str, hours: int = 24) -> List[PowerReading]:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with db_conn(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM power_readings WHERE meter_id=? AND timestamp >= ? ORDER BY timestamp",
                (meter_id, since)).fetchall()
        return [PowerReading.from_row(r) for r in rows]

    def export_report(self, device_id: str, days: int = 7) -> str:
        """Export a JSON power report for a device over N days."""
        self.get_device(device_id)
        meters = self.list_meters(device_id)
        report: Dict[str, Any] = {
            "device_id": device_id, "period_days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "meters": [],
        }
        for m in meters:
            readings = self.get_history(m.id, hours=days * 24)
            if readings:
                wattages = [r.wattage for r in readings]
                charges = [r.charge_pct for r in readings]
                report["meters"].append({
                    "meter_id": m.id, "type": m.type.value,
                    "current_state": m.state.value,
                    "avg_wattage": round(sum(wattages) / len(wattages), 4),
                    "max_wattage": max(wattages),
                    "min_charge_pct": min(charges),
                    "reading_count": len(readings),
                })
            else:
                report["meters"].append({"meter_id": m.id, "type": m.type.value,
                                          "reading_count": 0})
        events = self.get_events(device_id, limit=200)
        report["event_count"] = len(events)
        report["events"] = [asdict(e) for e in events[:20]]
        return json.dumps(report, indent=2)

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="BlackRoad Power Manager")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("report"); p.add_argument("device_id"); p.add_argument("--days", type=int, default=7)
    args = parser.parse_args(); pm = PowerManager()
    if args.cmd == "report": print(pm.export_report(args.device_id, days=args.days))
    else: parser.print_help()

if __name__ == "__main__":
    main()
