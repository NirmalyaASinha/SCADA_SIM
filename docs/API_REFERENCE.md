# API Reference

## Admin REST API (Port 9000)

### Authentication

```bash
curl -X POST http://localhost:9000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin@scada2024"}'
# Returns: {"success": true, "token": "eyJ0eXAi...", "username": "admin", "role": "admin"}
```

Include the token in subsequent requests:
```
Authorization: Bearer <token>
```

---

### Core Endpoints

```bash
# System health (no auth required)
GET http://localhost:9000/health

# List all registered nodes
GET http://localhost:9000/nodes
Authorization: Bearer <token>

# Grid overview (aggregated KPIs)
GET http://localhost:9000/grid/overview
Authorization: Bearer <token>
```

---

### Historian Endpoints

```bash
# Query historical telemetry — multi-node, multi-metric time-series
GET http://localhost:9000/historian/metrics
  ?nodes=GEN-001,SUB-001
  &metrics=Voltage,Current,Power
  &time_range=24H
Authorization: Bearer <token>
```

**Query Parameters:**

| Parameter    | Values                                              | Description                    |
|--------------|-----------------------------------------------------|--------------------------------|
| `nodes`      | Comma-separated node IDs (e.g., `GEN-001,SUB-001`) | Nodes to query                 |
| `metrics`    | `Voltage`, `Current`, `Power`, `Frequency`, `Temperature` | Metrics to retrieve      |
| `time_range` | `15m`, `1H`, `6H`, `24H`, `7D`                     | Historical window              |

**Response:**

```json
{
  "status": "success",
  "node_ids": ["GEN-001", "SUB-001"],
  "metrics": ["Voltage", "Current", "Power"],
  "time_range": "24H",
  "data": [
    {
      "time": "2026-02-27T10:00:00Z",
      "node_id": "GEN-001",
      "bus_voltage_kv": 130.4,
      "line_current_a": 450.2,
      "active_power_mw": 245.1
    }
  ],
  "count": 1440
}
```

---

### Control Endpoints

```bash
# Control node breaker (requires admin role)
POST http://localhost:9000/nodes/SUB-001/control/breaker
Authorization: Bearer <token>
Content-Type: application/json
Body: {"action": "open", "reason": "Maintenance"}

# Trigger cascade event (for testing)
POST http://localhost:9000/nodes/GEN-001/state_change
Authorization: Bearer <token>
Content-Type: application/json
Body: {"new_state": "TRIPPED", "reason": "Test cascade"}
```

---

## Node REST API (Ports 810x, 811x, 813x)

```bash
# Live telemetry (no auth required)
GET http://localhost:8111/telemetry

# Modbus connection info (no auth required)
GET http://localhost:8111/modbus/info

# Control breaker (requires auth)
POST http://localhost:8111/control/breaker
Authorization: Bearer <token>
Content-Type: application/json
Body: {"action": "open", "reason": "Emergency"}
```

---

## WebSocket Streams

- **Admin telemetry broadcast**: `ws://localhost:9001`
- **Node telemetry stream**: `ws://localhost:810{n}` (e.g., `ws://localhost:8102` for GEN-001)

Events pushed include: `telemetry_update`, `alarm_triggered`, `cascade_event`, `node_state_change`.
