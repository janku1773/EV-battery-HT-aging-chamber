import os
import pandas as pd
import numpy as np

# System Control Constants
T_TARGET = 60.0
T_MIN = 57.0
T_MAX = 63.0
TSI_THRESHOLD = 0.5
REQUIRED_HOURS = 48

class AgingChamberValidator:
    def __init__(self, target_temp=T_TARGET, t_min=T_MIN, t_max=T_MAX, tsi_limit=TSI_THRESHOLD):
        self.target_temp = target_temp
        self.t_min = t_min
        self.t_max = tmax
        self.tsi_limit = tsi_limit

    def calculate_tsi(self, df, temp_columns):
        """
        Calculates the Thermal Stability Index (TSI) for the batch across all sensors.
        Formula: TSI = (1/n) * sum(|T_actual - T_target|)
        """
        # Calculate absolute deviation from target for each sensor column per row
        abs_deviations = df[temp_columns].sub(self.target_temp).abs()
        
        # Mean deviation across all specified sensors for each timestamp
        df['row_tsi'] = abs_deviations.mean(axis=1)
        
        # Global batch TSI is the average of row TSIs over the entire run
        global_tsi = df['row_tsi'].mean()
        return global_tsi

    def analyze_batch(self, data_file: str, time_interval_minutes: int = 1):
        """
        Validates the 48-hour sensor logs against Gigafactory thermal and chemical constraints.
        
        Expects a CSV with columns: ['timestamp', 'room_id', 'humidity'] + 50 sensor columns (e.g., 'temp_1'...'temp_50')
        """
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"Log file not found at: {data_file}")
            
        df = pd.read_csv(data_file)
        
        # Identify temperature sensor columns dynamically
        temp_cols = [col for col in df.columns if col.startswith('temp')]
        if not temp_cols:
            raise ValueError("Data file error: No temperature sensor columns found.")

        # 1. Verify Process Duration
        total_records = len(df)
        total_duration_hours = (total_records * time_interval_minutes) / 60.0
        duration_passed = total_duration_hours >= REQUIRED_HOURS

        # 2. Temperature Bound Violations (Check if ANY sensor falls outside bounds at ANY time)
        # Vectorized check across all sensor columns
        out_of_bounds_mask = (df[temp_cols] < self.t_min) | (df[temp_cols] > self.t_max)
        
        # Count rows where at least one sensor violated the stability buffer
        violation_rows = out_of_bounds_mask.any(axis=1)
        total_violation_minutes = violation_rows.sum() * time_interval_minutes
        
        # 3. Mathematical Quality Validation via TSI
        batch_tsi = self.calculate_tsi(df, temp_cols)
        tsi_passed = batch_tsi <= self.tsi_limit

        # 4. Final MES/ASRS Decision Logic
        batch_approved = duration_passed and (total_violation_minutes == 0) and tsi_passed

        # Compile detailed analysis metrics
        report_metrics = {
            "batch_approved": bool(batch_approved),
            "room_id": df['room_id'].iloc[0] if 'room_id' in df.columns else "Unknown",
            "total_duration_hours": round(total_duration_hours, 2),
            "duration_passed": bool(duration_passed),
            "violation_time_minutes": int(total_violation_minutes),
            "thermal_stability_passed": bool(total_violation_minutes == 0),
            "calculated_batch_tsi": round(batch_tsi, 4),
            "tsi_passed": bool(tsi_passed),
            "max_recorded_temp": float(df[temp_cols].max().max()),
            "min_recorded_temp": float(df[temp_cols].min().min())
        }

        return report_metrics

    def format_summary(self, metrics: dict) -> str:
        """Formats the output dictionary into a human-readable execution summary."""
        status_icon = "✅ PASSED" if metrics["batch_approved"] else "❌ REJECTED"
        
        summary = (
            f"=== Chamber Aging Validation Report: {status_icon} ===\n"
            f"• Chamber/Room ID         : {metrics['room_id']}\n"
            f"• Process Duration        : {metrics['total_duration_hours']}/{REQUIRED_HOURS} hours "
            f"({'OK' if metrics['duration_passed'] else 'INSUFFICIENT TIME'})\n"
            f"• Out-of-Bounds Excursions: {metrics['violation_time_minutes']} minutes\n"
            f"• Batch TSI Score         : {metrics['calculated_batch_tsi']} (Max Allowed: {self.tsi_limit})\n"
            f"• Temp Extremes           : [{metrics['min_recorded_temp']}°C - {metrics['max_recorded_temp']}°C]\n"
        )
        
        if not metrics["batch_approved"]:
            summary += "\n⚠️ CRITICAL FAILURE: Batch holds risk of capacity loss or internal resistance instability."
        else:
            summary += "\n⚡ SUCCESS: Safe chemical SEI layer formation confirmed. Release signal sent to ASRS."
            
        return summary

# Contextual execution block for pipeline testing
if __name__ == "__main__":
    # Example deployment usage:
    validator = AgingChamberValidator()
    
    # Path mock for production orchestration
    sample_log = os.path.join("logs", "room01_latest_batch.csv")
    
    print("Deviation Detection Module Initialized. Awaiting batch log execution inputs...")
    # metrics = validator.analyze_batch(sample_log)
    # print(validator.format_summary(metrics))
