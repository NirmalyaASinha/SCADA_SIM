# 📊 Chart Visualization & CSV Export - Visual Guide

## What You'll See When You Use Historian

---

## **Step 1: Open Historian Tab**
```
┌─────────────────────────────────────────────────────────────────────┐
│ 🏠 SCADA OCC - Operations Control Centre                    👤 admin│
├─────────────────────────────────────────────────────────────────────┤
│ ▶ Grid Overview                                                     │
│ ▶ Node Management                                                   │
│ ▶ Control Center                                                    │
│ ▶ Alarms                                                            │
│ ▶ Security Monitoring                                               │
│ ▶ Historian           ◀️ YOU ARE HERE                               │
│ ▶ Modbus Monitor                                                    │
│ ▶ Audit Log                                                         │
│ ▶ Settings                                                          │
└─────────────────────────────────────────────────────────────────────┘

                          HISTORIAN PAGE
┌─────────────────────────────────────────────────────────────────┐
│ Historian                                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 📌 SELECT NODES (0 selected)                                   │
│ ┌─────────────────────────────────────────┐                    │
│ │ GEN-001  (generation)                   │                    │
│ │ GEN-002  (generation)                   │                    │
│ │ SUB-001  (transmission)                 │                    │
│ │ SUB-002  (transmission)                 │                    │
│ │ SUB-003  (transmission)                 │                    │
│ │ DIST-001 (distribution)                 │                    │
│ │ DIST-002 (distribution)                 │                    │
│ └─────────────────────────────────────────┘                    │
│ Hold Ctrl/Cmd to select multiple                               │
│                                                                 │
│ 📌 SELECT METRICS (0 selected)                                 │
│ [Voltage] [Current] [Power] [Frequency] [Temperature]          │
│                                                                 │
│ 📌 TIME RANGE                                                  │
│ [15m] [1H] [6H] [24H] [7D]                                    │
│                                                                 │
│ ┌─────────────────────────────────────────┐                    │
│ │ 📊                                      │                    │
│ │                                         │                    │
│ │ Select nodes and metrics to view chart  │                    │
│ │                                         │                    │
│ └─────────────────────────────────────────┘                    │
│                                                                 │
│ [📥 EXPORT CSV (disabled)]                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## **Step 2: Select a Node (GEN-001) and Metrics (Voltage)**

**Action**: 
- Click on `GEN-001` in the nodes list ✓
- Click on `[Voltage]` button ✓
- System auto-fetches data ✓

```
┌─────────────────────────────────────────────────────────────────┐
│ SELECT NODES (1 selected)                                       │
│ ┌─────────────────────────────────────────┐                    │
│ │ ✓ GEN-001  (generation) ◀️ SELECTED    │                    │
│ │   GEN-002  (generation)                 │                    │
│ │   SUB-001  (transmission)               │                    │
│ └─────────────────────────────────────────┘                    │
│                                                                 │
│ SELECT METRICS (1 selected)                                    │
│ [✓ Voltage] [Current] [Power] [Frequency] [Temperature]        │
│            ▲                                                     │
│            └─ Selected (green button)                           │
│                                                                 │
│ TIME RANGE                                                      │
│ [15m] [1H] [6H] [✓ 24H] [7D]                                  │
│                    ▲                                             │
│                    └─ Default selection                         │
│                                                                 │
│ ⏳ Fetching data...                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## **Step 3: Chart Appears with Data**

**Data fetched from backend**: 1,440 data points (24 hours × 60 minutes)

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────┐                    │
│ │                                         │                    │
│ │  132 kV ┐                 ┌────        │                    │
│ │         │    ╱╲          ╱ ╲  ╲      │                    │
│ │ 131 kV  │────╱  ╲────────    ───100%  │  🟢 Voltage
│ │         │       (voltage trend)       │     (1440 points)
│ │ 130 kV  │                             │                    │
│ │         │                             │                    │
│ │         └─────────────────────────────│                    │
│ │ 0%      ░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                    │
│ │                                   Now │                    │
│ │                                    ↑  │                    │
│ │                          Time scale   │                    │
│ └─────────────────────────────────────────┘                    │
│                                                                 │
│ LEGEND:                                                         │
│ 🟢 Voltage (1440 points)                                        │
│                                                                 │
│ [📥 EXPORT CSV (1440 rows)] ◀️ NOW ENABLED!                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Color codes used in charts**:
- 🟢 Metric 1: `#00e676` (Green - Energy color)
- 🔵 Metric 2: `#0288d1` (Blue)
- 🟡 Metric 3: `#ffab00` (Amber)
- 🔴 Metric 4: `#ff1744` (Red)
- 🟣 Metric 5: `#aa44ff` (Purple)

---

## **Step 4: Add More Nodes & Metrics**

**Action**: Select `SUB-001` node + `Power` metric

```
┌─────────────────────────────────────────────────────────────────┐
│ SELECT NODES (2 selected)                                       │
│ [✓ GEN-001] [SUB-001] ◀️ Add more nodes                        │
│                                                                 │
│ SELECT METRICS (2 selected)                                    │
│ [Voltage] [✓ Power] ◀️ Add more metrics                        │
│                                                                 │
│ ⏳ Fetching combined data for GEN-001 & SUB-001...             │
│                                                                 │
```

---

## **Step 5: Chart with Multiple Data Series**

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────┐                    │
│ │                                         │                    │
│ │ 350 MW ┐  ╱╲      ╱╲                   │  🟢 GEN-001_Power
│ │        │ ╱  ╲    ╱  ╲  ╱─────          │  🔵 SUB-001_Power
│ │ 250 MW ├─    ────     ─                │  🟡 GEN-001_Voltage
│ │        │                               │  🔴 SUB-001_Voltage
│ │ 150 MW ┤                               │
│ │        │                               │
│ │  50 MW └───────────────────────────────│
│ │                               Now      │
│ │  (4 data series, multiple colors)      │
│ └─────────────────────────────────────────┘                    │
│                                                                 │
│ LEGEND:                                                         │
│ 🟢 GEN-001_Voltage (1440 points)                                │
│ 🔵 GEN-001_Power   (1440 points)                                │
│ 🟡 SUB-001_Voltage (1440 points)                                │
│ 🔴 SUB-001_Power   (1440 points)                                │
│                                                                 │
│ [📥 EXPORT CSV (5760 rows)] ◀️ 4 series × 1440 points!         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## **Step 6: Export to CSV**

**Action**: User clicks `[📥 EXPORT CSV]` button

```
System generates file:
  → scada_historian_2025-02-27.csv

Browser automatically downloads it ✓

File contents (first few lines):
┌──────────────────────────────────────────────────────┐
│ timestamp,node_id,metric,value                       │
│ 2025-02-27T00:00:00Z,GEN-001,Voltage,132.450        │
│ 2025-02-27T00:00:00Z,GEN-001,Power,234.500          │
│ 2025-02-27T00:00:00Z,SUB-001,Voltage,130.210        │
│ 2025-02-27T00:00:00Z,SUB-001,Power,180.300          │
│ 2025-02-27T00:01:00Z,GEN-001,Voltage,132.890        │
│ 2025-02-27T00:01:00Z,GEN-001,Power,245.120          │
│ 2025-02-27T00:01:00Z,SUB-001,Voltage,130.560        │
│ 2025-02-27T00:01:00Z,SUB-001,Power,195.800          │
│ ... (5,760 rows for 4 series × 1440 points)         │
└──────────────────────────────────────────────────────┘
```

---

## **Step 7: Use the CSV Data**

### **In Excel**:
```
1. Open scada_historian_2025-02-27.csv in Excel
2. Create charts and pivot tables
3. Analyze trends, anomalies, patterns
```

### **In Python**:
```python
import pandas as pd

# Load the CSV
df = pd.read_csv('scada_historian_2025-02-27.csv')

# Display basic stats
print(df.describe())

# Filter by node
gen001_data = df[df['node_id'] == 'GEN-001']

# Plot using matplotlib
import matplotlib.pyplot as plt
gen001_data[gen001_data['metric'] == 'Voltage'].plot(x='timestamp', y='value')
plt.show()

# Export to other formats
df.to_parquet('data.parquet')  # For big data
df.to_sql('historian_data', con=engine)  # To database
```

### **In Google Sheets**:
```
1. Upload CSV to Google Drive
2. Open with Google Sheets
3. Use built-in charting and filtering
4. Share with team for analysis
```

---

## **Error Scenarios**

### **Scenario A: No Data for Time Range**
```
┌─────────────────────────────────────────────────────────────────┐
│ SELECT NODES (1 selected): GEN-001                              │
│ SELECT METRICS (1 selected): Frequency                          │
│ TIME RANGE: [7D] selected                                       │
│                                                                 │
│ ┌─────────────────────────────────────────┐                    │
│ │ 📊                                      │                    │
│ │                                         │                    │
│ │ No data available for selected          │                    │
│ │ parameters. Try expanding the           │                    │
│ │ time range.                             │                    │
│ │                                         │                    │
│ └─────────────────────────────────────────┘                    │
│                                                                 │
│ [📥 EXPORT CSV (disabled)]                                     │
│ ⚠️ No data to export.                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### **Scenario B: API Error**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ Query failed: Connection timeout                             │
│                                                                 │
│ [Retry] [Select Different Options]                             │
└─────────────────────────────────────────────────────────────────┘
```

### **Scenario C: No Selections**
```
┌─────────────────────────────────────────────────────────────────┐
│ SELECT NODES (0 selected)                                       │
│ SELECT METRICS (0 selected)                                    │
│                                                                 │
│ ┌─────────────────────────────────────────┐                    │
│ │ 📊                                      │                    │
│ │                                         │                    │
│ │ Select nodes and metrics to view chart  │                    │
│ │                                         │                    │
│ └─────────────────────────────────────────┘                    │
│                                                                 │
│ [📥 EXPORT CSV (disabled)]                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## **Real-World Examples**

### **Example 1: Monitor Generator Health Over 7 Days**
```
Nodes: GEN-001, GEN-002
Metrics: Voltage, Power, Frequency, Temperature
Time Range: 7D
Result: 5,040 rows (4 metrics × 1,440 minutes × 7 days / 1440)
```

**Chart shows**:
- How voltage varies daily
- Power generation peaks (day vs night)
- Frequency stability
- Temperature trends (normal ≈ 40-60°C)

**CSV can answer**:
- Average power output
- Peak hours
- Temperature anomalies
- Frequency deviations

---

### **Example 2: Debug Substation Voltage Drop**
```
Nodes: SUB-001, SUB-002, SUB-003
Metrics: Voltage
Time Range: 24H
Result: 1,440 rows (1 metric × 3 nodes × 1,440 minutes / 3)
```

**Chart shows**:
- Which substation has lowest voltage
- When voltage drops occur
- Pattern (consistent vs random)

**CSV can answer**:
- Min/max voltage per station
- Frequency of low-voltage events
- Duration of events
- Correlation with load

---

### **Example 3: Analyze Power Flow Pattern**
```
Nodes: GEN-001, GEN-002, SUB-001, DIST-001
Metrics: Power
Time Range: 24H
Result: 1,440 rows
```

**Chart shows**:
- When generators ramp up/down
- How much power reaches distribution
- Load profile throughout the day

**CSV for**:
- Peak shaving studies
- Load balancing analysis
- Capacity planning
- Demand forecasting

---

## 🎯 Summary: What Appears

| **Item** | **What Appears** |
|----------|-----------------|
| **Chart Type** | SVG line chart with grid background |
| **Data Points** | Up to 10,000+ depending on time range |
| **Colors** | 5 different colors (green, blue, amber, red, purple) |
| **Legend** | Shows metric name + point count |
| **X-Axis** | Time (from earliest to "Now") |
| **Y-Axis** | Metric values (auto-scaled) |
| **Interaction** | Select nodes, toggle metrics, pick time range |
| **CSV Export** | One-click download of all data |
| **File Format** | Standard CSV (timestamp, node_id, metric, value) |
| **Rows Generated** | nodes × metrics × data_points |

---

**Status**: ✅ **All features implemented and ready to use!**
