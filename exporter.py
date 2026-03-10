import requests
from prometheus_client import start_http_server, Gauge
import time
import re
import os

ASKOHEAT_URL = os.getenv("ASKOHEAT_URL", "http://192.168.3.13/_gethome.json")

temperature = Gauge("askoheat_temperature_celsius", "Boiler temperature")
power = Gauge("askoheat_power_watts", "Current heater power")
step = Gauge("askoheat_heater_step", "Active heater step")

def clean_number(value):
    m = re.search(r"[-+]?\d+(\.\d+)?", str(value))
    return float(m.group()) if m else 0

def fetch():
    r = requests.get(ASKOHEAT_URL, timeout=5)
    data = r.json()

    actual = data["ACTUAL_VALUES"]

    temperature.set(clean_number(actual["TEMP_SENSOR_0"]))
    power.set(clean_number(actual["ACTUAL_HEATER_LOAD_WATTS"]))
    step.set(clean_number(actual["ACTUAL_HEATER_STEP"]))

if __name__ == "__main__":
    start_http_server(9105)

    while True:
        try:
            fetch()
        except Exception as e:
            print("error:", e)

        time.sleep(10)

