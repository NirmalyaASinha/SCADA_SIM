# SCADA Platform Simulation System

A **production-faithful**, distributed SCADA (Supervisory Control and Data Acquisition) simulation platform designed for industrial control systems research, security testing, and educational purposes.

> ⚠️ **Security Warning**: This system intentionally includes realistic security vulnerabilities (unauthenticated Modbus TCP, legacy protocols) for research purposes. **DO NOT** deploy on production networks or expose to the internet.

---

## 🎯 Features

### ✨ Latest: Historian & Time-Series Analysis (v2.0)
- **Historical Data Queries**: Retrieve up to 7 days of telemetry data
- **Multi-Node Comparison**: Analyze voltage, current, power across any combination of nodes
- **Interactive Charts**: SVG-based visualization with auto-scaling axes
- **Data Export**: One-click CSV download for Excel/Python analysis
- **Automatic Refresh**: Charts update as you change selections
- **Database Backend**: TimescaleDB with 30-day rolling retention

### Architecture
- **7 Independent Node Services**: Generation stations (GEN), transmission substations (SUB), and distribution stations (DIST)
- **Distributed Deployment**: Nodes can run on different physical machines across a network
- **Admin Service**: Centralized monitoring and control console
- **Real-Time Telemetry**: WebSocket-based streaming (1-second updates)
- **Production Protocols**: Modbus TCP (S7-200 legacy mode), REST APIs, WebSocket

### Simulation Fidelity
- **Realistic Electrical Behavior**: 24-hour load profiles based on Indian grid patterns
- **Physics-Based Dynamics**: Thermal lag modeling (5-minute time constant for transformers)
- **Protection Systems**: Overcurrent, undervoltage, frequency deviation alarms with 5 priority levels
- **Operational Controls**: Circuit breaker operations, transformer tap changers (17 positions)

### Power Grid Cascade Engine ⚡
- **Grid Topology Awareness**: Accurate transmission line mapping (GEN → SUB → DIST → Consumers)
- **Cascade Computation**: Intelligent power flow calculation — downstream nodes only de-energize if ALL upstream sources trip
- **Real-Time Propagation**: Cascade events broadcast within 2 seconds to all dashboards
- **Consumer Impact Tracking**: Automatic household blackout count (up to 83,000 consumers in north + south zones)
- **Power Restoration**: Reverse cascade when breaker re-closes — nodes re-energize in order
- **Cascade History**: All cascade events logged to database with duration and impact metrics

### Modern Operator Dashboards 🎨
- **Admin Operations Control Center**: Unified grid overview with live KPI cards, topology map, and alarm panel
- **Sidebar Navigation**: 10 organized menu items (Grid Overview, Node Management, Control Center, Alarms, Security Monitoring, **Historian**, Modbus Monitor, Audit Log, Settings)
- **Historian Tab** ⭐: Query 15-minute to 7-day historical telemetry with multi-node, multi-metric selection
  - Interactive SVG line charts (voltage, current, power, frequency, temperature)
  - One-click CSV export for analysis
  - Automatic data refresh on metric selection changes
- **Node Operator Dashboards**: Single-line diagrams showing electrical topology, breaker states, and upstream/downstream status
- **Real-Time Styling**: Modern dark theme with neon green accents (#0a0a0f void background, #00e676 energy color)
- **Responsive Layout**: Works on desktop control room displays and mobile operator tablets
- **Live Data Badges**: Active alarms counter (amber), unauthorized Modbus connections (purple pulsing), session timer
- **Cascade Animation**: Visual representation of power flowing through grid — turns grey when de-energized

### Security Research Features
- **Intentionally Vulnerable Modbus TCP**: No authentication (S7-200 legacy compatibility)
- **Transaction Logging**: All Modbus reads/writes logged to database with source IP tracking
- **Connection Monitoring**: Active connection tracking with unauthorized access alerts
- **Audit Trail**: Complete security event logging with alarm history

### Technology Stack
- **Backend**: Python 3.11, FastAPI, asyncio
- **Database**: PostgreSQL + TimescaleDB (time-series optimization) with 30-day rolling retention
- **Protocols**: Modbus TCP (pymodbus), WebSockets, REST APIs
- **Frontend**: React 18 via jsDelivr CDN (single-file HTML, no build step)
- **Visualization**: SVG-based charts + Recharts integration ready
- **Deployment**: Docker + Docker Compose (v2)
- **Monitoring**: Prometheus + Grafana

---

## 🚀 Quick Start

### Requirements
- Docker Engine + Docker Compose v2 (`docker compose`)

### Single-Machine Deployment (Full System)

```bash
# 1. Clone the repository
git clone git@github.com:NirmalyaASinha/SCADA_SIM.git
cd SCADA_SIM

# 2. Start everything with one command
./launch.sh
```

That's it! The system will:
- Build all Docker images
- Start infrastructure (database, Redis, monitoring)
- Launch admin service
- Start all 7 node services
- Display all access URLs and credentials

**Access the system:**
- **Admin Dashboard**: http://localhost:3000 (login: `admin` / `admin@scada2024`)
- **Node Dashboards**: http://localhost:8101/ui through http://localhost:8133/ui
- **Grafana**: http://localhost:3001 (login: `admin` / `admin123`)

---

## 🌐 Cross-Machine Deployment

Deploy the admin console on one machine and nodes on separate machines (perfect for distributed testing).

### Setup

**Machine 1 (Admin + Infrastructure):**
```bash
# Get your IP address
hostname -I
# Example output: 192.168.1.100

# Start admin and infrastructure only
docker compose up -d timescaledb redis prometheus grafana admin_service
```

**Machine 2 (Node Station - e.g., SUB-001):**
```bash
# Clone the repository
git clone git@github.com:NirmalyaASinha/SCADA_SIM.git
cd SCADA_SIM

# Launch specific node with interactive dialog
./launch_node.sh SUB-001

# When prompted, enter the admin machine's IP:
# Enter Master IP: 192.168.1.100
```

The node will:
1. Prompt for the admin machine's IP address
2. Connect and register with the admin service
3. Start streaming telemetry
4. Become visible in the admin dashboard

**Repeat for more nodes on different machines.**

---

## ⚡ Power Grid Cascade Behavior

### How It Works

The SCADA system accurately models **grid topology and power flow cascades** — when one node trips, only the nodes that depend on it for power will de-energize.

**Topology (Electricity Flow):**
```
┌─ GEN-001 ─┐
└─ GEN-002 ─┤
            ├─→ SUB-001 ──→ DIST-001 ──→ 🏠 45,000 households (North)
            ├─→ SUB-002 ──→ DIST-002 ──→ 🏠 38,000 households (South)
            └─→ SUB-003 ──→ [end, no distribution]
```

**Cascade Rules:**
```
✅ GEN-001 trips, GEN-002 online
   → SUB nodes still have power from GEN-002
   → No cascade (resilient design)

❌ Both GEN-001 and GEN-002 trip
   → ALL SUB nodes lose upstream power
   → ALL DIST nodes de-energize
   → 83,000 consumers lose power
   → CRITICAL cascade event triggered
```

**Implementation:**
- PowerFlowEngine in `admin_service/master/power_flow.py` computes cascade every 2 seconds
- Node state changes (`ENERGIZED` → `TRIPPED`) immediately trigger cascade calculation
- Downstream nodes receive `/control/deenergize` POST from admin service
- All dashboard clients receive `cascade_event` WebSocket broadcast with affected household count
- Database logs every cascade event for historical analysis

---

## 📋 System Architecture

### Node Types

| Node ID   | Type          | Voltage  | Nominal Capacity | Modbus Port | Dashboard Port |
|-----------|---------------|----------|------------------|-------------|----------------|
| GEN-001   | Generation    | 380 kV   | 500 MW           | 5020        | 8101           |
| GEN-002   | Generation    | 380 kV   | 500 MW           | 5021        | 8103           |
| SUB-001   | Transmission  | 132 kV   | 300 MVA          | 5030        | 8111           |
| SUB-002   | Transmission  | 132 kV   | 300 MVA          | 5031        | 8113           |
| SUB-003   | Transmission  | 132 kV   | 300 MVA          | 5032        | 8115           |
| DIST-001  | Distribution  | 11 kV    | 50 MVA           | 5040        | 8131           |
| DIST-002  | Distribution  | 11 kV    | 50 MVA           | 5041        | 8133           |

### Port Reference

#### Admin Service
- **REST API**: 9000
- **WebSocket**: 9001
- **Dashboard**: 3000

#### Nodes (Pattern: REST +0, WebSocket +1, Dashboard = REST)
- **GEN-001**: REST 8101, WebSocket 8102, Modbus 5020
- **GEN-002**: REST 8103, WebSocket 8104, Modbus 5021
- **SUB-001**: REST 8111, WebSocket 8112, Modbus 5030
- **SUB-002**: REST 8113, WebSocket 8114, Modbus 5031
- **SUB-003**: REST 8115, WebSocket 8116, Modbus 5032
- **DIST-001**: REST 8131, WebSocket 8132, Modbus 5040
- **DIST-002**: REST 8133, WebSocket 8134, Modbus 5041

#### Monitoring
- **Prometheus**: 9090
- **Grafana**: 3001
- **TimescaleDB**: 5432 (internal)

---

## 🔐 Default Credentials

### Admin Dashboard (http://localhost:3000)

| Username         | Password         | Role      | Permissions                          |
|------------------|------------------|-----------|--------------------------------------|
| admin            | admin@scada2024  | Admin     | Full access (control + management)   |
| engineer         | eng@scada2024    | Engineer  | View + control nodes                 |
| viewer           | view@scada2024   | Viewer    | Read-only access                     |

### Node Operator Dashboards

| Node      | Dashboard URL              | Username         | Password       |
|-----------|----------------------------|------------------|----------------|
| GEN-001   | http://localhost:8101/ui   | operator_gen001  | gen001@scada   |
| GEN-002   | http://localhost:8103/ui   | operator_gen002  | gen002@scada   |
| SUB-001   | http://localhost:8111/ui   | operator_sub001  | sub001@scada   |
| SUB-002   | http://localhost:8113/ui   | operator_sub002  | sub002@scada   |
| SUB-003   | http://localhost:8115/ui   | operator_sub003  | sub003@scada   |
| DIST-001  | http://localhost:8131/ui   | operator_dist001 | dist001@scada  |
| DIST-002  | http://localhost:8133/ui   | operator_dist002 | dist002@scada  |

Note: These defaults can be overridden with `OPERATOR_USERNAME` and `OPERATOR_PASSWORD` in docker-compose.yml or .env.

### Monitoring Tools
- **Grafana**: `admin` / `admin123`

---

## 🛠️ Management Scripts

### Launch Scripts
```bash
./launch.sh              # Start full system (admin + all nodes)
./launch_node.sh SUB-001 # Start specific node (for remote machines)
```

### Operations
```bash
./status.sh              # Check health of all services
./logs.sh [service]      # View logs (all or specific service)
./stop.sh                # Stop all services
```

### Node Control CLI (continuous)
Use the built-in CLI to start/standby/isolate nodes from the terminal without opening the UI.

```bash
python3 tools/node_cli.py
```

What it does:
- Prompts for admin login
- Lists nodes with current state and power
- Lets you run `start`, `standby` (stop), or `isolate` in a loop until you exit

### Admin-to-Node Control Token
Admin control actions (start/standby/isolate/voltage) are forwarded to node services using a shared token.
Default token is set in docker compose as `MASTER_API_TOKEN: scada-master-token` for both admin and nodes.
If you change it, update it on both sides and rebuild.

### Examples
```bash
# View admin service logs
./logs.sh admin_service

# View GEN-001 logs
./logs.sh node_gen001

# Check system status
./status.sh

# Stop everything
./stop.sh
```

---

## � Historian Feature

### Overview
The **Historian Tab** in the admin dashboard provides time-series analysis and historical data retrieval for all nodes.

### Capabilities
- **Multi-Node Selection**: Query any combination of nodes simultaneously
- **Multi-Metric Analysis**: Voltage, Current, Power, Frequency, Temperature
- **Time Range Options**: 15-minute, 1-hour, 6-hour, 24-hour, 7-day windows
- **Interactive Visualization**: SVG line charts with color-coded metrics
- **CSV Export**: Download data for external analysis tools (Excel, Python, etc.)
- **Auto-Refresh**: Charts update automatically when selections change
- **Data Source**: PostgreSQL TimescaleDB with optimized queries

### Usage

1. **Navigate to Historian Tab** in admin dashboard sidebar (📊 icon)
2. **Select Nodes**: Hold Ctrl/Cmd to multi-select (e.g., GEN-001, GEN-002, SUB-001)
3. **Select Metrics**: Toggle buttons for Voltage, Current, Power, Frequency, Temperature
4. **Choose Time Range**: 15m, 1H, 6H, 24H, or 7D
5. **View Chart**: SVG visualization with Y-axis auto-scaling based on data
6. **Export CSV**: Click "Export CSV" button to download data with columns [timestamp, node_id, metric, value]

### Example Queries

**Query generation capacity over the last 6 hours:**
```
Nodes: GEN-001, GEN-002
Metrics: Power
Time Range: 6H
→ Chart shows MW output trend for both generators
```

**Compare substation voltages (24h):**
```
Nodes: SUB-001, SUB-002, SUB-003
Metrics: Voltage
Time Range: 24H
→ Identify voltage deviations and stability issues across transmission network
```

### API Endpoint

```bash
# Get historical metrics
curl "http://localhost:9000/historian/metrics?nodes=GEN-001,SUB-001&metrics=Voltage,Current,Power&time_range=24H" \
  -H "Authorization: Bearer <token>"

# Response structure
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
    },
    ...
  ],
  "count": 1440
}
```

### Data Retention
- **Interval**: 1-second telemetry snapshots
- **Retention**: 30 days rolling window
- **Table**: `node_telemetry` (TimescaleDB hypertable)
- **Indexing**: Optimized on (node_id, time DESC)

---

## �🔌 Modbus TCP Interface

### Connection Details

Each node exposes a **Modbus TCP server** (Unit ID 1-7) with **NO AUTHENTICATION** (S7-200 legacy mode).

**Example using Python:**
```python
from pymodbus.client import ModbusTcpClient

# Connect to SUB-001
client = ModbusTcpClient('localhost', port=5030)
client.connect()

# Read holding registers (address 40001-40010)
result = client.read_holding_registers(address=0, count=10, unit=3)
values = result.registers

print(f"Voltage: {values[0] / 100.0} kV")
print(f"Current: {values[1] / 100.0} A")
print(f"Active Power: {values[2] / 10.0} MW")

# Write coil to trip breaker (address 00001)
client.write_coil(address=0, value=False, unit=3)

client.close()
```

### Register Map (All Nodes)

**Holding Registers (Read-Only via Modbus):**
| Address | Name              | Scale Factor | Unit    | Example Value |
|---------|-------------------|--------------|---------|---------------|
| 40001   | Voltage           | 100          | kV      | 13200 → 132.0 |
| 40002   | Current           | 100          | A       | 15450 → 154.5 |
| 40003   | Active Power      | 10           | MW      | 2050 → 205.0  |
| 40004   | Reactive Power    | 10           | MVAr    | 450 → 45.0    |
| 40005   | Frequency         | 100          | Hz      | 5000 → 50.00  |
| 40006   | Power Factor      | 1000         | p.u.    | 950 → 0.950   |
| 40007   | Load Percentage   | 10           | %       | 855 → 85.5    |
| 40008   | Temperature       | 10           | °C      | 752 → 75.2    |
| 40009   | Alarm Code        | 1            | Enum    | 3 → MEDIUM    |
| 40010   | Tap Position      | 1            | Integer | 9 (SUB only)  |

**Coils (Read/Write):**
| Address | Name                    | Description                           |
|---------|-------------------------|---------------------------------------|
| 00001   | Breaker Status          | True = CLOSED, False = OPEN           |
| 00002   | Auto Mode               | True = AUTO, False = MANUAL           |
| 00003   | Alarm Acknowledge       | Write True to clear alarms            |
| 00004   | Emergency Stop          | Write True to trip breaker            |
| 00005   | Remote Control Enabled  | True = Remote, False = Local Only     |

**Security Notes:**
- All Modbus transactions are logged to the database (`modbus_transactions` table)
- Source IP addresses are tracked
- No authentication required → **Easy target for security research**

---

## 📊 Database Schema

### Key Tables

**node_registry**: Registered nodes and heartbeat status
**node_telemetry**: Time-series telemetry data (TimescaleDB hypertable with 30-day retention)
**modbus_transactions**: All Modbus read/write operations with source IP
**alarms**: Active and historical alarms with priority levels
**security_events**: Unauthorized access attempts and anomalies
**active_connections**: Real-time tracking of all connected clients
**cascade_events**: ⚡ NEW: All cascade events with trigger node, affected nodes, household impact, and restoration timestamp

### Direct Database Access

```bash
# Connect to TimescaleDB
docker exec -it scada_timescaledb psql -U scada -d scadadb

# Query recent telemetry
SELECT node_id, voltage, current, active_power, timestamp
FROM node_telemetry
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC
LIMIT 10;

# View Modbus transactions
SELECT node_id, function_code, address, value, client_ip, timestamp
FROM modbus_transactions
ORDER BY timestamp DESC
LIMIT 20;
```

---

## 🔬 Security Research Use Cases

### 1. Modbus TCP Attacks
- **Unauthorized Control**: Write coils without authentication
- **Data Exfiltration**: Read all registers from any node
- **DoS Testing**: Flood requests to Modbus ports

### 2. Man-in-the-Middle
- **Traffic Interception**: Analyze Modbus protocol structure
- **Replay Attacks**: Capture and replay control commands

### 3. Reconnaissance
- **Port Scanning**: Discover Modbus servers (ports 5020-5041)
- **Register Enumeration**: Map all available data points

### 4. Anomaly Detection Development
- All transactions logged to database → Perfect for ML/AI training
- Generate benign and malicious traffic patterns
- Test intrusion detection systems

**Example Attack Flow:**
```bash
# Scan for Modbus devices
nmap -p 5020-5041 <target-ip>

# Connect with Modbus client
python modbus_attack.py --host <ip> --port 5030

# Trip all breakers simultaneously
# (Logs will show in database with source IP)
```

---

## 🧩 Customization

### Adding Custom Nodes

1. **Define node in docker-compose.yml:**
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

2. **Update node simulation** in `node_service/simulation/` to add custom behavior

3. **Restart system:**
```bash
./stop.sh
./launch.sh
```

### Modifying Simulation Parameters

Edit `.env` file (copy from `.env.example`) or update docker-compose.yml:
```bash
# Speed up simulation (2x real-time)
SIM_SPEED=2.0

# Increase telemetry frequency (0.5 second updates)
TELEMETRY_INTERVAL=0.5
```

### Changing Load Profiles

Edit `node_service/simulation/base_node.py`:
```python
def get_load_factor(self) -> float:
    """Customize 24-hour load curve"""
    hour = datetime.now().hour
    # Your custom profile here
    return custom_load_curve[hour]
```

---

## 📈 Monitoring with Grafana

1. **Access Grafana**: http://localhost:3001
2. **Login**: `admin` / `admin123`
3. **Add TimescaleDB Data Source**:
  - Type: PostgreSQL
  - Host: `timescaledb:5432`
  - Database: `scadadb`
  - User: `scada`
  - Password: `scada123`
  - Enable TimescaleDB

4. **Create Dashboards**:
   - Grid frequency over time
   - Total generation vs. load
   - Alarm history
   - Modbus transaction rate

**Sample Query:**
```sql
SELECT
  time_bucket('1 minute', timestamp) AS time,
  AVG(frequency) as avg_frequency
FROM node_telemetry
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time
```

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker info

# View error logs
./logs.sh

# Clean restart
./stop.sh
docker compose down -v  # WARNING: Deletes database
./launch.sh
```

### Node Can't Connect to Admin (Cross-Machine)

```bash
# On admin machine, check firewall
sudo ufw status
sudo ufw allow 9000/tcp  # Admin REST API

# On node machine, test connectivity
curl http://<admin-ip>:9000/health

# Check if using correct IP
hostname -I  # On admin machine
```

### Database Connection Errors

```bash
# Wait longer for database startup
docker compose up -d timescaledb
sleep 15
docker compose up -d admin_service

# Check database logs
docker logs scada_timescaledb
```

### Port Conflicts

```bash
# Check what's using a port
sudo netstat -tulpn | grep 8101

# Change ports in .env file
GEN001_REST_PORT=8201  # Changed from 8101
```

---

## 📚 API Documentation

### Admin REST API (Port 9000)

**Authentication:**
```bash
# Login
curl -X POST http://localhost:9000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin@scada2024"}'

# Returns: {"success": true, "token": "eyJ0eXAi...", "username": "admin", "role": "admin"}
```

**Core Endpoints:**
```bash
# Get all registered nodes
curl http://localhost:9000/nodes \
  -H "Authorization: Bearer <token>"

# Get grid overview (aggregated KPIs)
curl http://localhost:9000/grid/overview \
  -H "Authorization: Bearer <token>"

# Get system health
curl http://localhost:9000/health
```

**⭐ Historian Endpoints (NEW):**
```bash
# Get historical metrics - Multi-node, multi-metric time-series data
curl "http://localhost:9000/historian/metrics?nodes=GEN-001,SUB-001&metrics=Voltage,Current&time_range=24H" \
  -H "Authorization: Bearer <token>"

# Query parameters:
# - nodes: Comma-separated node IDs (e.g., GEN-001,GEN-002,SUB-001)
# - metrics: Comma-separated metrics (Voltage,Current,Power,Frequency,Temperature)
# - time_range: 15m, 1H, 6H, 24H, or 7D
```

**Control Endpoints:**
```bash
# Control node breaker (requires admin role)
curl -X POST http://localhost:9000/nodes/SUB-001/control/breaker \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "open", "reason": "Maintenance"}'

# Trigger cascade event (for testing)
curl -X POST http://localhost:9000/nodes/GEN-001/state_change \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"new_state": "TRIPPED", "reason": "Test cascade"}'
```

### Node REST API (Port 810x, 811x, 813x)

```bash
# Get live telemetry (public endpoint)
curl http://localhost:8111/telemetry

# Get Modbus connection info
curl http://localhost:8111/modbus/info

# Control breaker (requires authentication)
curl -X POST http://localhost:8111/control/breaker \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "open", "reason": "Emergency"}'
```

---

## 📦 Project Structure

```
SCADA_SIM/
├── admin_service/           # Admin console service
│   ├── api/                 # REST API routes
│   ├── dashboard/           # React admin UI (modern dark theme)
│   ├── master/
│   │   ├── registry.py      # Node registration tracking
│   │   ├── connector.py     # Node connection manager
│   │   ├── aggregator.py    # Telemetry aggregation
│   │   ├── power_flow.py    # ⚡ Cascade engine
│   │   └── __init__.py
│   ├── websocket/           # WebSocket broadcaster for cascade events
│   └── main.py              # Entry point
│
├── node_service/            # Node service (used by all 7 nodes)
│   ├── api/                 # Node REST APIs (control, telemetry)
│   ├── dashboard/           # Operator UI (single-line diagrams)
│   ├── protocols/           # Modbus TCP server
│   ├── simulation/          # Physics simulation engine
│   │   ├── base_node.py     # Enhanced with cascade-aware states
│   │   ├── gen_node.py
│   │   ├── sub_node.py
│   │   └── dist_node.py
│   ├── websocket/           # Telemetry broadcaster
│   ├── startup_dialog.py    # IP selection for cross-machine deployment
│   └── main.py              # Entry point
│
├── database/
│   └── init.sql             # Schema + cascade_events table
│
├── tools/
│   └── node_cli.py          # CLI tool for node management
│
├── docker-compose.yml       # Full system deployment
├── docker-compose.nodes.yml # Single node deployment
├── prometheus.yml           # Monitoring configuration
│
├── launch.sh                # Start full system
├── launch_node.sh           # Start single node
├── stop.sh                  # Stop all services
├── status.sh                # Health check
├── logs.sh                  # View logs
├── Makefile                 # Alternative build/run commands
│
├── .env.example             # Environment variables template
└── README.md                # This file
```

---

## ⚙️ System Requirements

- **OS**: Linux (tested on Ubuntu 22.04), macOS, Windows (WSL2)
- **Docker**: 24.0+ with Docker Compose V2
- **RAM**: 4GB minimum, 8GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended
- **Disk**: 5GB for images + database
- **Network**: Ports 3000-9090 available

---

## 🚀 Recent Updates (Version 2.0 - Draft Second)

### ✨ New Features
- **⭐ Historian Tab**: Complete implementation of historical telemetry queries
  - Multi-node, multi-metric selection for time-series analysis
  - Interactive SVG line charts with auto-scaling
  - One-click CSV export for external analysis
  - Auto-refresh on metric/time-range selection changes
  - Supports 15m to 7-day time windows

### 🐛 Fixes & Improvements
- **Fixed CDN Links**: Migrated from unpkg.com to jsDelivr
  - Resolved 302 redirect issues preventing React from loading
  - Dashboard now loads reliably in all browsers
  - Fallback to production React libraries

- **Node Registration**: All 7 nodes now properly register with admin service
  - GEN-001, GEN-002, SUB-001, SUB-002, SUB-003, DIST-001, DIST-002 ✅
  - Real-time connection tracking via WebSocket
  - Heartbeat-based health monitoring

- **Dashboard Backend**: Enhanced API routes with historian support
  - New `/historian/metrics` endpoint for time-series queries
  - Improved error handling and validation
  - Optimized database queries for performance

### 📊 Database Enhancements
- `node_telemetry` table: 30-day rolling retention with TimescaleDB optimization
- Index optimization on (node_id, time DESC) for histogram queries
- Support for in-memory caching of recent data

### 🎨 UI/UX
- Modern dark theme fully operational
- Real-time telemetry updates (1-second intervals)
- Responsive design for desktop and tablet
- Snappy interactions with no lag

---

## 🤝 Contributing

This is a research/educational platform. Suggestions for improvements:
- Additional node types (e.g., renewable generation)
- More realistic protection relay logic
- Enhanced grid topology visualization (React Flow integration)
- Real-time anomaly detection using ML
- Additional industrial protocols (DNP3, IEC 61850)
- Historian charting with Recharts library
- Advanced power flow analysis tools

---

## 📄 License


This project is provided as-is for educational and research purposes. The intentional security vulnerabilities make it unsuitable for production deployment.

---

## 🙏 Acknowledgments

- **TimescaleDB** for time-series database optimization
- **PyModbus** for Modbus TCP implementation
- **FastAPI** for modern async Python APIs
- **React** for responsive UI components

---

## 📞 Support

For issues or questions:
1. Check the **Troubleshooting** section above
2. View logs: `./logs.sh`
3. Check service status: `./status.sh`
4. File an issue (if this is a Git repository)

---

**Built with ❤️ for Industrial Control Systems Security Research**
