import pytest
from battery_aging_logic import AgingRoom, MESManager, BatteryBatch

def test_temperature_tolerance():
    room = AgingRoom("Test_HT", 60, 3)
    assert room.check_temp_stability(62.9) == True
    assert room.check_temp_stability(63.1) == False
    assert room.check_temp_stability(57.0) == True

def test_full_process_success():
    mes = MESManager()
    batch = BatteryBatch("TEST_B")
    # Simulate perfect run
    mes.validate_process_step(batch, "HT1", "HT", 24, 24, 60)
    mes.validate_process_step(batch, "HT2", "HT", 12, 12, 60)
    mes.validate_process_step(batch, "LT1", "LT", 48, 48, 25)
    assert batch.status != "REJECTED"
