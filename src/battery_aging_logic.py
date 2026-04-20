import time
from datetime import datetime

class AgingRoom:
    """Represents a thermal chamber in the Gigafactory."""
    def __init__(self, room_id, target_temp, tolerance):
        self.room_id = room_id
        self.target_temp = target_temp
        self.tolerance = tolerance
        self.is_occupied = False

    def check_temp_stability(self, actual_temp):
        """Returns True if temperature is within the safety band."""
        return (self.target_temp - self.tolerance) <= actual_temp <= (self.target_temp + self.tolerance)

class BatteryBatch:
    """Represents a group of EV batteries undergoing aging."""
    def __init__(self, batch_id):
        self.batch_id = batch_id
        self.status = "IN_PROGRESS"
        self.logs = []
        self.rejection_reason = ""

    def add_log(self, step, duration, temperature, result):
        self.logs.append({
            "step": step,
            "duration_hrs": duration,
            "avg_temp": temperature,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })

class MESManager:
    """The central Manufacturing Execution System logic."""
    def __init__(self):
        # Redundant rooms: 2 High Temp (HT) and 2 Low Temp (LT)
        self.chambers = {
            "HT": [AgingRoom("HT_Room_A", 60, 3), AgingRoom("HT_Room_B", 60, 3)],
            "LT": [AgingRoom("LT_Room_C", 25, 3), AgingRoom("LT_Room_D", 25, 3)]
        }

    def find_available_room(self, room_type):
        for room in self.chambers[room_type]:
            if not room.is_occupied:
                return room
        return None

    def validate_process_step(self, batch, step_name, room_type, target_hrs, actual_hrs, actual_temp):
        """
        Critical validation for battery chemistry. 
        Failures here impact voltage capacity and charging safety.
        """
        room_ref = self.chambers[room_type][0]
        temp_valid = room_ref.check_temp_stability(actual_temp)
        time_valid = actual_hrs >= target_hrs

        if not temp_valid or not time_valid:
            batch.status = "REJECTED"
            batch.rejection_reason += f"[{step_name}] Deviation detected. "

        result = "PASSED" if (temp_valid and time_valid) else "FAILED"
        batch.add_log(step_name, actual_hrs, actual_temp, result)
        return result

def simulate_gigafactory_cycle():
    mes = MESManager()
    batch = BatteryBatch("BATCH-EV-LION-001")
    
    print(f"--- Starting Process for {batch.batch_id} ---")

    # Step 1: 24h High Temp Aging
    mes.validate_process_step(batch, "Initial_HT_Aging", "HT", 24, 24.2, 60.5)

    # Step 2: 12h High Temp Re-entry (Post-Processing)
    mes.validate_process_step(batch, "Secondary_HT_Aging", "HT", 12, 12.1, 59.8)

    # Step 3: 48h Low Temp Stabilization
    mes.validate_process_step(batch, "Final_LT_Soaking", "LT", 48, 48.5, 25.2)

    # Final Quality Gate
    if batch.status != "REJECTED":
        batch.status = "APPROVED_FOR_ASSEMBLY"

    print(f"Final Status: {batch.status}")
    if batch.rejection_reason:
        print(f"Reason: {batch.rejection_reason}")

if __name__ == "__main__":
    simulate_gigafactory_cycle()
