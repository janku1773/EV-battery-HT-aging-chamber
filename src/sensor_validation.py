import pandas as pd
from temperature_limits import MIN_TEMP, MAX_TEMP

def validate_sensor_data(csv_path):
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    df["out_of_tolerance"] = ~df["temperature_c"].between(MIN_TEMP, MAX_TEMP)
    return df

if __name__ == "__main__":
    df = validate_sensor_data("data/sensor_temperature_sample.csv")
    print(df.head())
