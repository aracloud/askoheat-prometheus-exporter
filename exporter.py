import os
import re
import time

import requests
from prometheus_client import Gauge, start_http_server


ASKOHEAT_URL = os.getenv(
    "ASKOHEAT_URL",
    "http://192.168.3.13/_gethome.json",
)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

temperature = Gauge(
    "askoheat_temperature_celsius",
    "Current ASKOHEAT boiler temperature",
)

temperature_limit = Gauge(
    "askoheat_temperature_limit_celsius",
    "Current ASKOHEAT temperature limit",
)

power = Gauge(
    "askoheat_power_watts",
    "Current ASKOHEAT heater power",
)

heater_load_percent = Gauge(
    "askoheat_heater_load_percent",
    "Current ASKOHEAT heater load as percentage of maximum power",
)

heater_step = Gauge(
    "askoheat_heater_step",
    "Current ASKOHEAT heater step",
)

max_power = Gauge(
    "askoheat_max_power_watts",
    "Maximum ASKOHEAT heater power",
)

load_setpoint = Gauge(
    "askoheat_load_setpoint_watts",
    "Configured ASKOHEAT load setpoint",
)

legionella_days = Gauge(
    "askoheat_legionella_days_since",
    "Days since the last ASKOHEAT legionella cycle",
)

heater_relay_state = Gauge(
    "askoheat_heater_relay_state",
    "ASKOHEAT heater relay state (1=ON, 0=OFF)",
    ["heater"],
)

pump_state = Gauge(
    "askoheat_pump_state",
    "ASKOHEAT pump state (1=ON, 0=OFF)",
)

pump_trail_seconds = Gauge(
    "askoheat_pump_trail_seconds",
    "ASKOHEAT pump trail countdown in seconds",
)

error_state = Gauge(
    "askoheat_error",
    "ASKOHEAT error state (1=error, 0=OK)",
)

device_up = Gauge(
    "askoheat_up",
    "ASKOHEAT API availability (1=up, 0=down)",
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def extract_number(value):
    """
    Extract the first integer or floating-point number from a string.

    Examples:
        '56 °C'                  -> 56.0
        '3333 xZa_0058'          -> 3333.0
        'last time 5d 14h (=5.61 d)' -> 5.61
        'none'                   -> 0.0
    """
    if value is None:
        return 0.0

    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))

    if match:
        return float(match.group())

    return 0.0


def extract_relay_state(value):
    """
    ASKOHEAT status flags use internal xZa codes.

    xZa_0026 = ON
    xZa_0027 = OFF

    Some relay strings contain transitions, e.g.
    'xZa_0027 -> 33s xZa_0028'

    For now we use the first state code.
    """

    value = str(value)

    if "xZa_0026" in value:
        return 1.0

    return 0.0


# ---------------------------------------------------------------------------
# ASKOHEAT API
# ---------------------------------------------------------------------------

def fetch_data():
    response = requests.get(
        ASKOHEAT_URL,
        timeout=5,
    )

    response.raise_for_status()

    return response.json()


# ---------------------------------------------------------------------------
# Update metrics
# ---------------------------------------------------------------------------

def update_metrics(data):
    info = data["ASKOHEAT_PLUS_INFO"]
    actual = data["ACTUAL_VALUES"]
    inputs = data["SET_INPUTS"]
    status = data["STATUS_FLAGS"]

    # Temperature
    temp = extract_number(actual["TEMP_SENSOR_0"])
    temperature.set(temp)

    # Temperature limit
    temp_limit = extract_number(status["TEMPERATURE_LIMIT"])
    temperature_limit.set(temp_limit)

    # Current heater power
    current_power = extract_number(
        actual["ACTUAL_HEATER_LOAD_WATTS"]
    )
    power.set(current_power)

    # Maximum heater power
    maximum_power = extract_number(info["MAX_POWER"])
    max_power.set(maximum_power)

    # Heater load %
    if maximum_power > 0:
        load_percent = (current_power / maximum_power) * 100
    else:
        load_percent = 0

    heater_load_percent.set(load_percent)

    # Heater step
    current_step = extract_number(
        actual["ACTUAL_HEATER_STEP"]
    )
    heater_step.set(current_step)

    # Load setpoint
    setpoint = extract_number(
        inputs["SET_LOAD_SETPOINT"]
    )
    load_setpoint.set(setpoint)

    # Legionella days
    legionella = extract_number(
        info["LEGIO_INFO"]
    )
    legionella_days.set(legionella)

    # Heater relays
    for number in range(1, 4):
        key = f"HEATER_{number}_RELAY"

        state = extract_relay_state(
            status[key]
        )

        heater_relay_state.labels(
            heater=str(number)
        ).set(state)

    # Pump
    pump_state.set(
        extract_relay_state(
            status["PUMP_RELAY"]
        )
    )

    # Pump trail countdown
    pump_trail_seconds.set(
        extract_number(
            status["PUMP_TRAIL_COUNTDOWN"]
        )
    )

    # Error
    error_code = extract_number(
        data.get("MODBUS_VAL_ERROR_STATUS", 0)
    )

    error_state.set(
        1 if error_code != 0 else 0
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("Starting ASKOHEAT Prometheus Exporter")
    print(f"ASKOHEAT URL: {ASKOHEAT_URL}")
    print(f"Poll interval: {POLL_INTERVAL}s")

    start_http_server(9105)

    while True:

        try:
            data = fetch_data()

            update_metrics(data)

            device_up.set(1)

            print("ASKOHEAT data updated")

        except Exception as exc:

            device_up.set(0)

            print(
                f"ERROR: Could not read ASKOHEAT: {exc}"
            )

        time.sleep(POLL_INTERVAL)

