# Database Schema Reference

## Overview

The platform uses **PostgreSQL 15** with the **TimescaleDB** extension for time-series optimization.

**Connection:**
```bash
docker exec -it scada_timescaledb psql -U scada -d scadadb
```

---

## Tables

### `node_registry`
Registered nodes and their last heartbeat.

| Column        | Type        | Description                        |
|---------------|-------------|------------------------------------|
| node_id       | TEXT (PK)   | Unique node identifier (e.g., GEN-001) |
| node_type     | TEXT        | generation / transmission / distribution |
| ip_address    | TEXT        | Node's IP address                  |
| rest_port     | INTEGER     | REST API port                      |
| modbus_port   | INTEGER     | Modbus TCP port                    |
| last_heartbeat| TIMESTAMPTZ | Timestamp of most recent heartbeat |
| status        | TEXT        | ONLINE / OFFLINE                   |

---

### `node_telemetry` *(TimescaleDB hypertable)*
1-second telemetry snapshots from all nodes. 30-day rolling retention.

| Column              | Type        | Description                    |
|---------------------|-------------|--------------------------------|
| time                | TIMESTAMPTZ | Snapshot timestamp (PK part)   |
| node_id             | TEXT        | Node identifier (PK part)      |
| bus_voltage_kv      | FLOAT       | Bus voltage in kV              |
| line_current_a      | FLOAT       | Line current in A              |
| active_power_mw     | FLOAT       | Active power in MW             |
| reactive_power_mvar | FLOAT       | Reactive power in MVAr         |
| frequency_hz        | FLOAT       | Frequency in Hz                |
| power_factor        | FLOAT       | Power factor (0–1)             |
| load_percent        | FLOAT       | Load percentage (0–100)        |
| transformer_temp_c  | FLOAT       | Transformer temperature in °C  |
| alarm_code          | INTEGER     | Active alarm priority level    |
| tap_position        | INTEGER     | Transformer tap position (SUBs)|

**Indexes:** `(node_id, time DESC)` for fast per-node historical queries.

---

### `modbus_transactions`
Every Modbus read/write with full audit information.

| Column        | Type        | Description                   |
|---------------|-------------|-------------------------------|
| id            | SERIAL (PK) | Transaction ID                |
| timestamp     | TIMESTAMPTZ | When the transaction occurred |
| node_id       | TEXT        | Target node                   |
| client_ip     | TEXT        | Source IP address             |
| function_code | INTEGER     | Modbus function code          |
| address       | INTEGER     | Register/coil address         |
| value         | TEXT        | Written value (writes only)   |

---

### `alarms`
Active and historical alarms with priority levels.

| Column      | Type        | Description                              |
|-------------|-------------|------------------------------------------|
| id          | SERIAL (PK) | Alarm ID                                 |
| timestamp   | TIMESTAMPTZ | When the alarm triggered                 |
| node_id     | TEXT        | Originating node                         |
| alarm_type  | TEXT        | OVERCURRENT / UNDERVOLTAGE / FREQUENCY / etc. |
| priority    | INTEGER     | 1 (CRITICAL) → 5 (INFO)                 |
| message     | TEXT        | Human-readable alarm description         |
| acknowledged| BOOLEAN     | Whether the alarm has been acknowledged  |

---

### `security_events`
Unauthorized access attempts and anomalies.

| Column     | Type        | Description                  |
|------------|-------------|------------------------------|
| id         | SERIAL (PK) | Event ID                     |
| timestamp  | TIMESTAMPTZ | When the event occurred      |
| event_type | TEXT        | UNAUTHORIZED_ACCESS / ANOMALY |
| source_ip  | TEXT        | Source IP address            |
| detail     | TEXT        | Event description            |

---

### `cascade_events`
Power cascade trigger and restoration events.

| Column            | Type        | Description                          |
|-------------------|-------------|--------------------------------------|
| id                | SERIAL (PK) | Event ID                             |
| triggered_at      | TIMESTAMPTZ | When the cascade began               |
| restored_at       | TIMESTAMPTZ | When power was restored (nullable)   |
| trigger_node_id   | TEXT        | Node that caused the cascade         |
| affected_nodes    | TEXT[]      | Array of de-energized node IDs       |
| household_impact  | INTEGER     | Number of consumers without power    |

---

## Useful Queries

```sql
-- Recent telemetry (last hour)
SELECT node_id, bus_voltage_kv, active_power_mw, timestamp
FROM node_telemetry
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC
LIMIT 20;

-- Modbus activity by source IP
SELECT client_ip, count(*) AS requests, max(timestamp) AS last_seen
FROM modbus_transactions
GROUP BY client_ip
ORDER BY requests DESC;

-- Active (unacknowledged) alarms
SELECT node_id, alarm_type, priority, message, timestamp
FROM alarms
WHERE acknowledged = FALSE
ORDER BY priority ASC, timestamp DESC;

-- Cascade events summary
SELECT trigger_node_id, household_impact,
       triggered_at, restored_at,
       EXTRACT(EPOCH FROM (restored_at - triggered_at)) AS duration_seconds
FROM cascade_events
ORDER BY triggered_at DESC;
```
