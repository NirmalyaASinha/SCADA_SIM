# SCADA Platform Simulation System

A **production-faithful**, distributed SCADA (Supervisory Control and Data Acquisition) simulation platform for industrial control systems research, security testing, and education.

> ⚠️ **Security Warning**: This system intentionally includes realistic vulnerabilities (unauthenticated Modbus TCP, legacy protocols) for research purposes. **Do not** deploy on production networks or expose to the internet.

---

## What Is This?

This platform simulates a complete power grid — from generation stations through transmission substations to distribution points — with realistic physics, real industrial protocols, and operator dashboards.

It is designed to be a safe, self-contained environment for:

- **Learning** how SCADA/ICS systems work in practice
- **Security research** — testing attack tools and defensive controls on Modbus TCP and REST interfaces
- **Building IDS/ICS datasets** — all transactions are logged, enabling labelled dataset generation
- **Demonstrating** grid cascade failures and power restoration in a lab setting
- **Teaching** industrial protocol behavior without real infrastructure

---

## Key Features

### Simulation Fidelity
- Physics-based electrical behavior with 24-hour Indian grid load profiles
- Thermal lag modeling (5-minute time constant for transformers)
- Protection systems: overcurrent, undervoltage, and frequency deviation alarms with 5 priority levels
- Circuit breaker operations and transformer tap changers (17 tap positions)

### Grid Cascade Engine
- Accurate transmission line topology (GEN → SUB → DIST → Consumers)
- A downstream node de-energizes only when **all** upstream sources have tripped
- Cascade events broadcast to all dashboards within 2 seconds
- Automatic household blackout count (up to 83,000 consumers across North and South zones)
- Full cascade history stored in the database with duration and impact metrics

### Historian & Time-Series Analysis
- Query up to 7 days of per-node telemetry (Voltage, Current, Power, Frequency, Temperature)
- Multi-node, multi-metric selection with interactive SVG line charts
- One-click CSV export for analysis in Excel or Python
- Charts auto-refresh when metric or time-range selection changes

### Industrial Protocols
- **Modbus TCP** (unauthenticated, S7-200 legacy mode) — 10 holding registers + 5 coils per node
- **REST APIs** — full control and telemetry endpoints with JWT authentication
- **WebSocket streams** — 1-second real-time telemetry and cascade event broadcasts

### Security Logging
- Every Modbus read/write logged to the database with source IP and timestamp
- Unauthorized access detection and security event trail
- Audit log accessible from the admin dashboard sidebar

### Operator Dashboards
- **Admin Operations Control Center**: live KPI cards, grid topology map, alarm panel, historian tab
- **Node Operator UIs**: single-line diagrams showing breaker states, upstream/downstream status, and live telemetry
- Modern dark theme (`#0a0a0f` background, `#00e676` energy accent)
- Responsive — works on desktop control room displays and tablets

### Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, asyncio |
| Database | PostgreSQL 15 + TimescaleDB (30-day rolling retention) |
| Protocols | Modbus TCP (pymodbus), WebSockets, REST |
| Frontend | React 18 via jsDelivr CDN (single-file HTML, no build step) |
| Deployment | Docker + Docker Compose v2 |
| Monitoring | Prometheus + Grafana |

---

## Quick Start

**Requirements:** Docker Engine + Docker Compose v2

```bash
# Clone and launch the full system
git clone git@github.com:NirmalyaASinha/SCADA_SIM.git
cd SCADA_SIM
./launch.sh
```

The launch script:
1. Builds all Docker images
2. Starts the database and infrastructure (TimescaleDB, Redis, Prometheus, Grafana)
3. Launches the admin service
4. Starts all 7 node services
5. Prints all access URLs and credentials

### Access Points

| Service | URL | Credentials |
|---|---|---|
| Admin Dashboard | http://localhost:3000 | `admin` / `admin@scada2024` |
| Grafana | http://localhost:3001 | `admin` / `admin123` |
| Admin REST API | http://localhost:9000 | — |
| Node Dashboards | http://localhost:8101/ui through :8133/ui | See credentials table below |

---

## System Architecture

### Grid Topology

```
┌─ GEN-001 ─┐
└─ GEN-002 ─┤
            ├─→ SUB-001 ──→ DIST-001 ──→ 🏠 45,000 households (North)
            ├─→ SUB-002 ──→ DIST-002 ──→ 🏠 38,000 households (South)
            └─→ SUB-003 ──→ [end, no distribution]
```

**Cascade example:**
```
✅ GEN-001 trips, GEN-002 online
   → SUBs still receive power from GEN-002
   → No cascade (resilient design)

❌ Both GEN-001 and GEN-002 trip
   → All SUB nodes lose upstream power → de-energize
   → All DIST nodes de-energize
   → 83,000 consumers lose power
   → CRITICAL cascade event logged
```

The cascade engine runs in `admin_service/master/power_flow.py` and recalculates every 2 seconds. When a node's state changes, downstream nodes receive a `/control/deenergize` call and all dashboards get a `cascade_event` WebSocket broadcast.

### Node Reference

| Node ID  | Type         | Voltage | Capacity | Modbus | REST | Dashboard |
|----------|--------------|---------|----------|--------|------|-----------|
| GEN-001  | Generation   | 380 kV  | 500 MW   | 5020   | 8101 | :8101/ui  |
| GEN-002  | Generation   | 380 kV  | 500 MW   | 5021   | 8103 | :8103/ui  |
| SUB-001  | Transmission | 132 kV  | 300 MVA  | 5030   | 8111 | :8111/ui  |
| SUB-002  | Transmission | 132 kV  | 300 MVA  | 5031   | 8113 | :8113/ui  |
| SUB-003  | Transmission | 132 kV  | 300 MVA  | 5032   | 8115 | :8115/ui  |
| DIST-001 | Distribution | 11 kV   | 50 MVA   | 5040   | 8131 | :8131/ui  |
| DIST-002 | Distribution | 11 kV   | 50 MVA   | 5041   | 8133 | :8133/ui  |

### Port Summary

| Service       | Port(s)         |
|---------------|-----------------|
| Admin REST    | 9000            |
| Admin WS      | 9001            |
| Admin UI      | 3000            |
| Node REST     | 8101, 8103, 8111, 8113, 8115, 8131, 8133 |
| Node WS       | 8102, 8104, 8112, 8114, 8116, 8132, 8134 |
| Modbus TCP    | 5020, 5021, 5030, 5031, 5032, 5040, 5041 |
| Prometheus    | 9090            |
| Grafana       | 3001            |
| TimescaleDB   | 5432 (internal) |

---

## Default Credentials

### Admin Dashboard (`http://localhost:3000`)

| Username | Password        | Role     | Access                        |
|----------|-----------------|----------|-------------------------------|
| admin    | admin@scada2024 | Admin    | Full — control + management   |
| engineer | eng@scada2024   | Engineer | View + control nodes          |
| viewer   | view@scada2024  | Viewer   | Read-only                     |

### Node Operator Dashboards

| Node     | URL                      | Username          | Password      |
|----------|--------------------------|-------------------|---------------|
| GEN-001  | http://localhost:8101/ui | operator_gen001   | gen001@scada  |
| GEN-002  | http://localhost:8103/ui | operator_gen002   | gen002@scada  |
| SUB-001  | http://localhost:8111/ui | operator_sub001   | sub001@scada  |
| SUB-002  | http://localhost:8113/ui | operator_sub002   | sub002@scada  |
| SUB-003  | http://localhost:8115/ui | operator_sub003   | sub003@scada  |
| DIST-001 | http://localhost:8131/ui | operator_dist001  | dist001@scada |
| DIST-002 | http://localhost:8133/ui | operator_dist002  | dist002@scada |

> Defaults can be overridden via `OPERATOR_USERNAME` and `OPERATOR_PASSWORD` in `docker-compose.yml` or `.env`.

### Monitoring
- **Grafana**: `admin` / `admin123`

---

## Cross-Machine Deployment

Deploy the admin console on one machine and individual nodes on separate machines — ideal for distributed network testing.

**Machine 1 — Admin + Infrastructure:**
```bash
hostname -I  # Note this IP, e.g. 192.168.1.100
docker compose up -d timescaledb redis prometheus grafana admin_service
```

**Machine 2 — Node Station (e.g. SUB-001):**
```bash
git clone git@github.com:NirmalyaASinha/SCADA_SIM.git
cd SCADA_SIM
./launch_node.sh SUB-001
# When prompted: Enter Master IP: 192.168.1.100
```

Each node will:
1. Prompt for the admin machine's IP
2. Register with the admin service
3. Begin streaming 1-second telemetry
4. Appear live in the admin dashboard

Repeat for additional nodes on different machines.

---

## Management Scripts

```bash
./launch.sh               # Start full system (admin + all 7 nodes)
./launch_node.sh SUB-001  # Start a single node (cross-machine deployment)
./status.sh               # Health check all services
./logs.sh [service]       # View logs — omit service name for all
./stop.sh                 # Stop all services
```

**Node Control CLI** — manage nodes from the terminal without opening the dashboard:
```bash
python3 tools/node_cli.py
# Prompts for admin credentials, lists node states, then loops:
# Commands: start | standby | isolate | exit
```

**Log examples:**
```bash
./logs.sh admin_service    # Admin service logs
./logs.sh node_gen001      # GEN-001 logs
./logs.sh node_sub001      # SUB-001 logs
```

---

## API at a Glance

### Authentication

```bash
curl -X POST http://localhost:9000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin@scada2024"}'
# {"success": true, "token": "eyJ0eXAi...", "role": "admin"}
```

### Key Endpoints

```bash
# Live node list
curl http://localhost:9000/nodes -H "Authorization: Bearer <token>"

# Grid overview KPIs
curl http://localhost:9000/grid/overview -H "Authorization: Bearer <token>"

# Historical telemetry (Historian)
curl "http://localhost:9000/historian/metrics?nodes=GEN-001,SUB-001&metrics=Voltage,Power&time_range=6H" \
  -H "Authorization: Bearer <token>"

# Control a node breaker
curl -X POST http://localhost:9000/nodes/SUB-001/control/breaker \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"action": "open", "reason": "Maintenance"}'
```

See [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) for the complete API reference.

---

## Modbus TCP at a Glance

Each node exposes an **unauthenticated** Modbus TCP server (S7-200 legacy mode):

```python
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient('localhost', port=5030)  # SUB-001
client.connect()

result = client.read_holding_registers(address=0, count=10, unit=3)
print(f"Voltage: {result.registers[0] / 100.0} kV")   # reg 40001
print(f"Power:   {result.registers[2] / 10.0} MW")    # reg 40003

client.write_coil(0, False, unit=3)  # Trip breaker
client.close()
```

All Modbus transactions are logged with source IP. See [`docs/MODBUS_REFERENCE.md`](docs/MODBUS_REFERENCE.md) for the full register and coil map.

---

## Project Structure

```
SCADA_SIM/
├── admin_service/            # Centralized monitoring and control
│   ├── api/                  # REST API (port 9000)
│   ├── dashboard/            # Admin web UI (port 3000, React)
│   ├── master/
│   │   ├── registry.py       # Node registration and heartbeat
│   │   ├── connector.py      # Node connection manager
│   │   ├── aggregator.py     # Telemetry aggregation
│   │   └── power_flow.py     # Cascade engine
│   ├── websocket/            # Grid telemetry broadcaster (port 9001)
│   └── main.py
│
├── node_service/             # Shared service used by all 7 nodes
│   ├── api/                  # Node REST API
│   ├── dashboard/            # Operator UI (single-line diagrams)
│   ├── protocols/            # Modbus TCP server
│   ├── simulation/           # Physics simulation engine
│   │   ├── base_node.py      # Shared base class (cascade-aware states)
│   │   ├── gen_node.py       # Generation station behavior
│   │   ├── sub_node.py       # Transmission substation behavior
│   │   └── dist_node.py      # Distribution station behavior
│   ├── websocket/            # Telemetry broadcaster
│   ├── startup_dialog.py     # Admin IP selection (cross-machine)
│   └── main.py
│
├── database/
│   └── init.sql              # Schema: telemetry, alarms, cascade events
│
├── tools/
│   └── node_cli.py           # CLI tool for node management
│
├── docs/                     # Detailed reference documentation
│   ├── API_REFERENCE.md      # REST API and WebSocket reference
│   ├── MODBUS_REFERENCE.md   # Register map, coils, Python examples
│   ├── DATABASE_SCHEMA.md    # Table definitions and useful queries
│   ├── SECURITY_RESEARCH.md  # Attack scenarios, IDS dataset guides
│   ├── CUSTOMIZATION.md      # Adding nodes, load profiles, Grafana
│   └── TROUBLESHOOTING.md    # Common problems and solutions
│
├── docker-compose.yml        # Full system deployment
├── docker-compose.nodes.yml  # Single-node deployment
├── prometheus.yml            # Monitoring configuration
├── Makefile                  # Alternative build/run commands
├── .env.example              # Environment variables template
│
├── launch.sh                 # Start full system
├── launch_node.sh            # Start single node (cross-machine)
├── stop.sh                   # Stop all services
├── status.sh                 # Health check
└── logs.sh                   # View service logs
```

---

## System Requirements

| | Minimum | Recommended |
|---|---|---|
| OS | Linux (Ubuntu 22.04+), macOS, Windows (WSL2) | Linux |
| Docker | 24.0+ with Compose V2 | Latest |
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Disk | 5 GB | 10 GB |
| Network | Ports 3000–9090 available | — |

---

## Documentation Index

| Document | Contents |
|---|---|
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Admin and node REST endpoints, authentication, WebSocket events |
| [docs/MODBUS_REFERENCE.md](docs/MODBUS_REFERENCE.md) | Full register map, coil map, Python client examples |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | Table definitions, indexes, useful SQL queries |
| [docs/SECURITY_RESEARCH.md](docs/SECURITY_RESEARCH.md) | Attack scenarios, dataset generation, responsible use |
| [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md) | Adding nodes, simulation parameters, Grafana setup |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common problems and solutions |
| [HISTORIAN_IMPLEMENTATION.md](HISTORIAN_IMPLEMENTATION.md) | Historian feature implementation details |
| [CHART_VISUALIZATION_GUIDE.md](CHART_VISUALIZATION_GUIDE.md) | SVG chart implementation guide |
| [QUICK_ACCESS.md](QUICK_ACCESS.md) | Quick-access URLs for all services |

---

## Contributing

This is a research and educational platform. Contributions welcome in these areas:

- Additional node types (renewable generation, battery energy storage)
- More realistic protection relay logic
- Additional industrial protocols (DNP3, IEC 61850)
- Enhanced grid topology visualization (e.g., React Flow)
- Real-time anomaly detection integration
- Advanced power flow analysis tools

---

## License

Provided as-is for educational and research purposes. The intentional security vulnerabilities make it unsuitable for production deployment.

---

## Acknowledgments

- **TimescaleDB** — time-series database optimization
- **PyModbus** — Modbus TCP implementation
- **FastAPI** — modern async Python API framework
- **React** — responsive operator UI components

---

*Built for Industrial Control Systems Security Research*
