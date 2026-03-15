# Modbus TCP Reference

Each node exposes a **Modbus TCP server** with **no authentication** (S7-200 legacy mode), intentionally vulnerable for security research purposes.

## Connection Details

| Node     | Modbus Port | Unit ID |
|----------|-------------|---------|
| GEN-001  | 5020        | 1       |
| GEN-002  | 5021        | 2       |
| SUB-001  | 5030        | 3       |
| SUB-002  | 5031        | 4       |
| SUB-003  | 5032        | 5       |
| DIST-001 | 5040        | 6       |
| DIST-002 | 5041        | 7       |

---

## Register Map

### Holding Registers (Read-Only, FC03)

| Address | Name            | Scale | Unit  | Example               |
|---------|-----------------|-------|-------|-----------------------|
| 40001   | Voltage         | 100   | kV    | 13200 → 132.0 kV      |
| 40002   | Current         | 100   | A     | 15450 → 154.5 A       |
| 40003   | Active Power    | 10    | MW    | 2050 → 205.0 MW       |
| 40004   | Reactive Power  | 10    | MVAr  | 450 → 45.0 MVAr       |
| 40005   | Frequency       | 100   | Hz    | 5000 → 50.00 Hz       |
| 40006   | Power Factor    | 1000  | p.u.  | 950 → 0.950           |
| 40007   | Load Percentage | 10    | %     | 855 → 85.5 %          |
| 40008   | Temperature     | 10    | °C    | 752 → 75.2 °C         |
| 40009   | Alarm Code      | 1     | Enum  | 3 → MEDIUM priority   |
| 40010   | Tap Position    | 1     | Int   | 9 (SUB nodes only)    |

### Coils (Read/Write, FC01/FC05)

| Address | Name                   | Description                        |
|---------|------------------------|------------------------------------|
| 00001   | Breaker Status         | True = CLOSED, False = OPEN        |
| 00002   | Auto Mode              | True = AUTO, False = MANUAL        |
| 00003   | Alarm Acknowledge      | Write True to clear alarms         |
| 00004   | Emergency Stop         | Write True to trip breaker         |
| 00005   | Remote Control Enabled | True = Remote, False = Local Only  |

---

## Python Example

```python
from pymodbus.client import ModbusTcpClient

# Connect to SUB-001 (port 5030, unit 3)
client = ModbusTcpClient('localhost', port=5030)
client.connect()

# Read holding registers (40001–40010)
result = client.read_holding_registers(address=0, count=10, unit=3)
values = result.registers

print(f"Voltage:      {values[0] / 100.0} kV")
print(f"Current:      {values[1] / 100.0} A")
print(f"Active Power: {values[2] / 10.0} MW")

# Trip the breaker (write False to coil 00001)
client.write_coil(address=0, value=False, unit=3)

client.close()
```

---

## Security Notes

- All Modbus transactions are logged to the `modbus_transactions` database table.
- Source IP addresses are tracked for every read/write operation.
- No authentication is required — this is **intentional** for security research.
- See [SECURITY_RESEARCH.md](SECURITY_RESEARCH.md) for attack scenario guidance.
