"""Tests for BlackRoad Power Manager."""
import pytest
from power_manager import PowerManager, MeterType, PowerEventType, PowerState

@pytest.fixture
def pm(tmp_path):
    return PowerManager(db_path=tmp_path / "test.db")

@pytest.fixture
def device(pm):
    return pm.register_device("dev-001", "Edge Node", shutdown_threshold=3.0)

@pytest.fixture
def battery_meter(pm, device):
    return pm.add_meter(device.id, "battery", capacity_wh=50.0, name="Main Battery")

@pytest.fixture
def solar_meter(pm, device):
    return pm.add_meter(device.id, "solar", capacity_wh=0.0, name="Solar Panel")

def test_register_device(pm):
    d = pm.register_device("dev-x", "Pi Zero")
    assert d.name == "Pi Zero"
    assert d.shutdown_threshold == 3.0

def test_register_device_idempotent(pm):
    pm.register_device("dev-y", "Device Y", shutdown_threshold=5.0)
    d2 = pm.register_device("dev-y", "Device Y updated")
    assert d2.name == "Device Y updated"

def test_add_meter(pm, device):
    m = pm.add_meter(device.id, "main", capacity_wh=100.0)
    assert m.type == MeterType.MAIN
    assert m.capacity_wh == 100.0

def test_log_power(pm, battery_meter):
    r = pm.log_power(battery_meter.id, voltage=12.0, current=1.5, charge_pct=80.0)
    assert r.voltage == 12.0
    assert r.current_draw == 1.5
    assert r.wattage == 18.0
    assert r.charge_pct == 80.0

def test_log_power_clamps_charge(pm, battery_meter):
    r = pm.log_power(battery_meter.id, 12.0, 0.5, charge_pct=150.0)
    assert r.charge_pct == 100.0
    r2 = pm.log_power(battery_meter.id, 12.0, 0.5, charge_pct=-10.0)
    assert r2.charge_pct == 0.0

def test_calculate_wattage(pm, battery_meter):
    pm.log_power(battery_meter.id, 12.0, 2.0, 90.0)
    w = pm.calculate_wattage(battery_meter.id)
    assert w == 24.0

def test_estimate_runtime(pm, device, battery_meter):
    pm.log_power(battery_meter.id, 12.0, 2.0, 80.0)
    # 50Wh * 0.8 = 40Wh remaining / 24W = 1.667h
    runtime = pm.estimate_runtime(device.id)
    assert runtime is not None
    assert runtime > 0

def test_estimate_runtime_no_battery(pm):
    d = pm.register_device("dev-z", "No battery device")
    assert pm.estimate_runtime(d.id) is None

def test_trigger_event(pm, device):
    ev = pm.trigger_event(device.id, "charge_start", value=85.0)
    assert ev.type == PowerEventType.CHARGE_START
    assert ev.value == 85.0

def test_low_battery_auto_event(pm, device, battery_meter):
    # Charge at 10% (below LOW threshold) should trigger discharge event
    pm.log_power(battery_meter.id, 3.7, 0.5, charge_pct=10.0)
    events = pm.get_events(device.id)
    assert len(events) > 0

def test_critical_battery_auto_event(pm, device, battery_meter):
    pm.log_power(battery_meter.id, 3.2, 0.5, charge_pct=4.0)
    events = pm.get_events(device.id)
    assert any(e.type == PowerEventType.LOW_BATTERY for e in events)

def test_power_budget_check(pm, device, battery_meter):
    pm.log_power(battery_meter.id, 12.0, 1.0, 70.0)
    result = pm.power_budget_check([device.id])
    assert device.id in result
    assert result[device.id]["total_wattage"] == 12.0

def test_power_budget_unknown_device(pm):
    result = pm.power_budget_check(["nonexistent"])
    assert "nonexistent" in result
    assert "error" in result["nonexistent"]

def test_power_state_normal(pm, battery_meter):
    pm.log_power(battery_meter.id, 12.0, 1.0, 80.0)
    m = pm.get_meter(battery_meter.id)
    assert m.state == PowerState.NORMAL

def test_power_state_low(pm, battery_meter):
    pm.log_power(battery_meter.id, 10.0, 0.5, 15.0)
    m = pm.get_meter(battery_meter.id)
    assert m.state == PowerState.LOW

def test_power_state_critical(pm, battery_meter):
    pm.log_power(battery_meter.id, 3.2, 0.2, 4.0)
    m = pm.get_meter(battery_meter.id)
    assert m.state == PowerState.CRITICAL

def test_solar_state_always_charging(pm, device, solar_meter):
    m = pm.get_meter(solar_meter.id)
    assert m.state == PowerState.CHARGING

def test_get_history(pm, battery_meter):
    pm.log_power(battery_meter.id, 12.0, 1.0, 90.0)
    pm.log_power(battery_meter.id, 11.8, 1.0, 85.0)
    history = pm.get_history(battery_meter.id, hours=1)
    assert len(history) == 2

def test_export_report(pm, device, battery_meter):
    pm.log_power(battery_meter.id, 12.0, 1.5, 75.0)
    report = pm.export_report(device.id, days=1)
    import json
    data = json.loads(report)
    assert data["device_id"] == device.id
    assert len(data["meters"]) == 1
