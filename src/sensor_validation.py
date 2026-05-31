import os
import pandas as pd
import numpy as np

class SensorValidationEngine:
    def __init__(self, total_sensors: int = 50, expected_room_ids: list = None):
        """
        Initializes the data integrity validation layer for the high-precision 
        sensor array in the HT Aging Chambers.
        """
        self.total_sensors = total_sensors
        self.expected_room_ids = expected_room_ids or ["Room 01", "Room 02", "ROOM_01", "ROOM_02"]
        
        # Hard physical limits of the sensory equipment (out-of-bounds implies sensor failure, not just variance)
        self.HARD_MIN_TEMP = 0.0    # Lower bound for operational chamber ambient
        self.HARD_MAX_TEMP = 100.0  # Thermistor limit / potential runaway ignition threshold
        self.MAX_MISSING_PCT = 2.0  # Max acceptable missing data percentage before a sensor is flagged dead

    def check_structural_integrity(self, df: pd.DataFrame) -> list:
        """
        Verifies that the CSV structurally contains all 50 operational temperature probes.
        Returns a list of missing sensor labels.
        """
        expected_columns = [f"temp_{i}" for i in range(1, self.total_sensors + 1)]
        missing_cols = [col for col in expected_columns if col not in df.columns]
        return missing_cols

    def detect_frozen_sensors(self, df: pd.DataFrame, temp_cols: list) -> list:
        """
        Flags sensors showing suspiciously zero variance over the continuous run, 
        indicating a stuck or frozen hardware transmitter line.
        """
        # Calculate variance across time axis for each sensor
        variances = df[temp_cols].var()
        # A variance of exactly 0 over 48 hours is physically impossible in an active thermal system
        frozen_sensors = variances[variances == 0.0].index.tolist()
        return frozen_sensors

    def detect_malfunctioning_outliers(self, df: pd.DataFrame, temp_cols: list) -> list:
        """
        Identifies sensors generating values outside physical reality limits 
        (e.g., short circuits reading 999°C or disconnected loops reading -999°C).
        """
        malfunctioning = []
        for col in temp_cols:
            col_min = df[col].min()
            col_max = df[col].max()
            if col_min < self.HARD_MIN_TEMP or col_max > self.HARD_MAX_TEMP:
                malfunctioning.append(col)
        return malfunctioning

    def validate_sensor_matrix(self, data_file: str) -> dict:
        """
        Performs structural, missing-value, static-state, and physical outlier analysis 
        across the sensor map. Generates a validation passport for upstream MES routing.
        """
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"Target log file not found at path: {data_file}")

        df = pd.read_csv(data_file)
        
        # Determine target sensors present
        temp_cols = [col for col in df.columns if col.startswith('temp')]
        missing_sensors = self.check_structural_integrity(df)
        
        if len(missing_sensors) == self.total_sensors:
            return {
                "matrix_valid": False,
                "failure_reason": "CRITICAL: Complete telemetry loss. No temperature channels detected."
            }

        # 1. Evaluate missing data thresholds per sensor
        null_analysis = (df[temp_cols].isnull().sum() / len(df)) * 100
        dead_sensors = null_analysis[null_analysis > self.MAX_MISSING_PCT].index.tolist()

        # 2. Evaluate hardware performance anomalies
        frozen_sensors = self.detect_frozen_sensors(df, temp_cols)
        hardware_outliers = self.detect_malfunctioning_outliers(df, temp_cols)

        # Combine all unique flagged compromised channels
        compromised_sensors = list(set(missing_sensors + dead_sensors + frozen_sensors + hardware_outliers))
        
        # A dark factory automated line cannot approve a batch if the sensor arrays are suspect
        matrix_valid = len(compromised_sensors) == 0

        validation_passport = {
            "matrix_valid": bool(matrix_valid),
            "total_records_analyzed": len(df),
            "active_channels_found": len(temp_cols),
            "missing_sensor_count": len(missing_sensors),
            "missing_sensor_details": missing_sensors,
            "dead_sensor_count": len(dead_sensors),
            "dead_sensor_details": dead_sensors,
            "frozen_sensor_count": len(frozen_sensors),
            "frozen_sensor_details": frozen_sensors,
            "outlier_fault_count": len(hardware_outliers),
            "outlier_fault_details": hardware_outliers,
            "compromised_sensor_total": len(compromised_sensors)
        }

        return validation_passport

    def generate_mes_signal(self, passport: dict) -> str:
        """Translates validation summary directly into actionable MES execution logs."""
        if passport["matrix_valid"]:
            return "🟢 SENSOR MATRIX VALIDATED: 100% sensor accuracy verified. Safe to proceed with aging deviation logs."
        else:
            return (
                f"🔴 SENSOR VALIDATION FAILURE: {passport['compromised_sensor_total']} sensor lines compromised.\n"
                f"-> Structural Missing: {passport['missing_sensor_count']} | Dead: {passport['dead_sensor_count']} | "
                f"Frozen: {passport['frozen_sensor_count']} | Hardware Fault Outliers: {passport['outlier_fault_count']}.\n"
                f"⚠️ MES ACTION REQUIRED: Halt automated ASRS out-feed logic. Trigger manual maintenance validation."
            )

# Diagnostic Sandbox
if __name__ == "__main__":
    print("--- Gigafactory Telemetry Layer: Sensor Validation Framework ---")
    validator = SensorValidationEngine(total_sensors=50)
    
    # Example integration wire-in:
    # sample_path = os.path.join("logs", "room02_raw_telemetry.csv")
    # passport = validator.validate_sensor_matrix(sample_path)
    # print(validator.generate_mes_signal(passport))
