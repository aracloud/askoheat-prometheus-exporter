# ASKOHEAT Prometheus Exporter

Prometheus exporter for the **ASKOHEAT F+** boiler heating element.

The exporter fetches data from the device JSON API and exposes Prometheus metrics.

## Features

Exports:

* boiler temperature
* heater power
* heater step

## Metrics

```
askoheat_temperature_celsius
askoheat_power_watts
askoheat_heater_step
```

## Docker

Build:

```
docker build -t askoheat-exporter .
```

Run:

```
docker run -p 9105:9105 \
-e ASKOHEAT_URL=http://<askoheat-ip>/_gethome.json \
askoheat-exporter
```

Metrics endpoint:

```
http://localhost:9105/metrics
```

## Docker Compose

```
docker compose up -d
```

## Prometheus configuration

```
scrape_configs:
  - job_name: "askoheat"
    static_configs:
      - targets: ["localhost:9105"]
```

