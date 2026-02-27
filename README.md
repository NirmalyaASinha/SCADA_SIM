# SCADA Platform Simulation System

A **production-faithful**, distributed SCADA (Supervisory Control and Data Acquisition) simulation platform designed for industrial control systems research, security testing, and educational purposes.

> ⚠️ **Security Warning**: This system intentionally includes realistic security vulnerabilities (unauthenticated Modbus TCP, legacy protocols) for research purposes. **DO NOT** deploy on production networks or expose to the internet.

---

## 🎯 Features

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

### Security Research Features
- **Intentionally Vulnerable Modbus TCP**: No authentication (S7-200 legacy compatibility)
- **Transaction Logging**: All Modbus reads/writes logged to database with source IP tracking
- **Connection Monitoring**: Active connection tracking with unauthorized access alerts
- **Audit Trail**: Complete security event logging with alarm history

### Technology Stack
- **Backend**: Python 3.11, FastAPI, asyncio
- **Database**: PostgreSQL + TimescaleDB (time-series optimization)
- **Protocols**: Modbus TCP (pymodbus), WebSockets
- **Frontend**: React 18 (single-file HTML, no build step)
- **Deployment**: Docker + Docker Compose
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

## 🔌 Modbus TCP Interface

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

# Returns: {"access_token": "eyJ0eXAi...", "token_type": "bearer"}
```

**Endpoints:**
```bash
# Get all registered nodes
curl http://localhost:9000/nodes

# Get grid overview (aggregated KPIs)
curl http://localhost:9000/grid/overview

# Control node breaker (requires admin role)
curl -X POST http://localhost:9000/nodes/SUB-001/control/breaker \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "open", "reason": "Maintenance"}'
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
SCADA_SIM_2/
├── admin_service/           # Admin console service
│   ├── api/                 # REST API routes
│   ├── dashboard/           # React admin UI
│   ├── master/              # Registry, connector, aggregator
│   ├── websocket/           # WebSocket broadcaster
│   └── main.py              # Entry point
│
├── node_service/            # Node service (used by all 7 nodes)
│   ├── api/                 # Node REST API
│   ├── dashboard/           # Operator UI
│   ├── protocols/           # Modbus TCP server
│   ├── simulation/          # Physics simulation engine
│   ├── websocket/           # Telemetry broadcaster
│   ├── startup_dialog.py    # IP selection dialog
│   └── main.py              # Entry point
│
├── database/
│   └── init.sql             # Database schema + initial data
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

## 🤝 Contributing

This is a research/educational platform. Suggestions for improvements:
- Additional node types (e.g., renewable generation)
- More realistic protection relay logic
- Enhanced grid topology visualization
- Additional industrial protocols (DNP3, IEC 61850)

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
