# Customization Guide

## Adding a Custom Node

### 1. Define the node in `docker-compose.yml`

```yaml
node_custom001:
  build: ./node_service
  environment:
    - NODE_ID=CUSTOM-001
    - NODE_TYPE=generation
    - MASTER_IP=admin_service
    - REST_PORT=8141
    - MODBUS_PORT=5050
```

### 2. Customize simulation behavior

Edit `node_service/simulation/` to add node-specific logic:

- `base_node.py` — base class, shared behavior and states
- `gen_node.py` — generation station overrides
- `sub_node.py` — transmission substation overrides
- `dist_node.py` — distribution station overrides

### 3. Restart the system

```bash
./stop.sh
./launch.sh
```

---

## Modifying Simulation Parameters

Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

```bash
# Speed up simulation (2× real-time)
SIM_SPEED=2.0

# Faster telemetry updates (every 0.5 seconds)
TELEMETRY_INTERVAL=0.5

# Extend data retention (days)
TELEMETRY_RETENTION_DAYS=60
```

---

## Changing Load Profiles

Edit `node_service/simulation/base_node.py`:

```python
def get_load_factor(self) -> float:
    """Customize the 24-hour load curve."""
    hour = datetime.now().hour
    # Replace with your custom load profile
    return custom_load_curve[hour]
```

The default profile models **Indian grid patterns** with morning and evening peaks.

---

## Grafana Monitoring Setup

1. Access Grafana at `http://localhost:3001` (login: `admin` / `admin123`)
2. Add a PostgreSQL data source:
   - **Host**: `timescaledb:5432`
   - **Database**: `scadadb`
   - **User**: `scada`
   - **Password**: `scada123`
   - Enable **TimescaleDB** toggle
3. Create custom dashboards. Sample query:

```sql
SELECT
  time_bucket('1 minute', timestamp) AS time,
  AVG(frequency_hz)                  AS avg_frequency
FROM node_telemetry
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time
```

Useful dashboard ideas:
- Grid frequency over time
- Total generation vs. load
- Alarm event frequency
- Modbus transaction rate

---

## Admin-to-Node Control Token

Admin control commands are authenticated with a shared token:

```yaml
# docker-compose.yml (both admin and nodes)
MASTER_API_TOKEN: scada-master-token
```

If you change the token, update it on **both** admin and all node services, then rebuild:

```bash
docker compose build
./launch.sh
```
