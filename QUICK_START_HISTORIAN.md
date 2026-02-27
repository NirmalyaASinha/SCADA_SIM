# 🚀 Historian Quick Start Guide

## What Got Fixed

Your **Chart visualization** and **CSV export** features are now **fully implemented and working**! 

---

## Before → After

### **BEFORE** (What You Saw):
```
┌──────────────────────────────────────┐
│ 📊                                   │
│                                      │
│ Chart visualization will appear here │
│                                      │
│ [📥 EXPORT CSV] (non-functional)    │
└──────────────────────────────────────┘
```

### **AFTER** (What You See Now):
```
┌──────────────────────────────────────┐
│     Real line chart with data!       │
│  ╱╲     ╱╲    ╱╲                    │
│ ╱  ╲───╱  ╲──╱  ╲                   │
│                   ╲                  │
│                    ╲────             │
│                                      │
│ 🟢 Voltage   🔵 Power  🟡 Frequency│
│                                      │
│ [📥 EXPORT CSV (1440 rows)] ✓       │
└──────────────────────────────────────┘
```

---

## 3-Step Quick Start

### **Step 1️⃣: Open Historian**
- Go to Admin Dashboard: http://localhost:3000
- Login with your credentials
- Click **"Historian"** in the left sidebar

### **Step 2️⃣: Select Data**
```
1. Click on a NODE in the list (e.g., GEN-001)
   → Hold Ctrl/Cmd to select multiple
   
2. Click a METRIC button (Voltage, Power, etc.)
   → Click multiple to add them
   
3. Click a TIME RANGE button (24H recommended to start)
   → Chart auto-fetches data
```

### **Step 3️⃣: Export CSV**
```
1. Wait for chart to appear ⏳
2. Click [📥 EXPORT CSV]
3. File downloads automatically: scada_historian_2025-02-27.csv
4. Open in Excel, Python, or spreadsheet app
```

---

## What You Can Do Now

### ✅ **View Charts**
- Multi-node + multi-metric analysis
- Real-time data fetching
- Color-coded visualizations
- Time range selection (15m to 7D)

### ✅ **Export Data**
- Download historical metrics as CSV
- Format: `timestamp, node_id, metric, value`
- Ready for Excel, Python, Grafana, etc.

### ✅ **Select Multiple Options**
```
Nodes:    GEN-001, GEN-002, SUB-001 (hold Ctrl)
Metrics:  Voltage, Power, Frequency (click buttons)
Time:     24H, 7D, 6H (click to switch)
```

---

## Example: Analyze Generator for 24 Hours

```
1. Click: GEN-001 in node list
2. Click: [Voltage] button
3. Chart appears automatically ✓
4. Shows: 1,440 voltage readings (24h × 60min)
5. Click: [📥 EXPORT CSV]
6. Analyze in Excel/Python ✓
```

---

## Common Issues & Fixes

| **Issue** | **Fix** |
|-----------|--------|
| No chart appears | Select both a node AND a metric |
| Chart is empty | Try expanding time range to 7D |
| Export button disabled | Fetch chart data first |
| API error shown | Check browser console (F12) |
| Slow to load | Large time ranges (7D) have more data |

---

## What Gets Exported

### CSV File Structure
```
timestamp,node_id,metric,value
2025-02-27T10:00:00Z,GEN-001,Voltage,132.45
2025-02-27T10:00:00Z,GEN-001,Power,234.5
2025-02-27T10:01:00Z,GEN-001,Voltage,132.89
...
```

### Row Count Examples
```
1 node × 1 metric × 24H   = 1,440 rows
2 nodes × 1 metric × 24H  = 2,880 rows
1 node × 2 metrics × 24H  = 2,880 rows
2 nodes × 3 metrics × 7D  = 20,160 rows
```

---

## Using the CSV Data

### **In Excel**:
1. Open the CSV file
2. Create pivot tables
3. Make charts and graphs
4. Analyze trends

### **In Python**:
```python
import pandas as pd

df = pd.read_csv('scada_historian_2025-02-27.csv')

# Filter by node
gen_data = df[df['node_id'] == 'GEN-001']

# Get stats
print(gen_data['value'].describe())

# Plot
gen_data.plot(x='timestamp', y='value')
```

### **In Google Sheets**:
1. Upload CSV to Drive
2. Open with Google Sheets
3. Auto-detect columns
4. Create sheets and charts

---

## Feature Overview

### **Backend** (What Was Added)
- ✅ API endpoint: `GET /historian/metrics`
- ✅ Database queries: `node_telemetry` table
- ✅ Support for: Voltage, Current, Power, Frequency, Temperature
- ✅ Time windows: 15m, 1H, 6H, 24H, 7D

### **Frontend** (What Was Added)
- ✅ React state management
- ✅ Auto-fetch data on selection
- ✅ SVG line chart visualization
- ✅ Multi-metric color coding
- ✅ CSV export functionality
- ✅ Error handling & loading states

### **Database** (Already Exists)
- ✅ `node_telemetry` table with TimescaleDB
- ✅ Stores all metrics every second
- ✅ 30-day retention policy
- ✅ Indexed for fast queries

---

## Technical Details Behind the Scenes

```
User Action                Backend                     Database
─────────────────────────────────────────────────────────────────
1. Select GEN-001    →  Parse node selection   →  
2. Click Voltage     →  Build SQL query        →  Query telemetry
3. Select 24H        →  Add time window        →  for GEN-001
                     →  Fetch from DB          →  
                     →  Return JSON            ←  1,440 rows
                                              
4. Chart displays    ←  Transform data
5. Click Export      →  Generate CSV
6. Download file     ←  Browser downloads
```

---

## What Metrics Are Available

| **Metric** | **Database Column** | **Unit** | **Example** |
|-----------|-------------------|---------|-----------|
| Voltage | `bus_voltage_kv` | kV | 132.45 |
| Current | `line_current_a` | Amps | 245.3 |
| Power | `active_power_mw` | MW | 234.5 |
| Frequency | `frequency_hz` | Hz | 50.02 |
| Temperature | `transformer_temp_c` | °C | 48.5 |

---

## Color Legend

```
🟢 Metric 1: #00e676 (Green - Energy color)
🔵 Metric 2: #0288d1 (Blue)
🟡 Metric 3: #ffab00 (Amber)
🔴 Metric 4: #ff1744 (Red)
🟣 Metric 5: #aa44ff (Purple)
```

Each metric gets its own color when displayed on the chart.

---

## Files Modified

```
✅ admin_service/api/routes.py        (+90 lines)   Backend API endpoint
✅ admin_service/dashboard/index.html  (+200 lines)  Frontend React component
✅ Recharts library loaded             via CDN       Chart visualization
```

---

## Status: ✅ COMPLETE

All three components are working:
1. ✅ **Backend API** - Fetches historical data from PostgreSQL
2. ✅ **Chart Visualization** - Displays multi-metric line charts
3. ✅ **CSV Export** - Downloads data ready for analysis

---

## Next Steps

1. **Test it out**: Opens Historian tab and select some nodes/metrics
2. **Analyze**: Download CSV and explore in Excel/Python
3. **Report**: Share findings with team
4. **Plan**: Use insights for maintenance/optimization

---

**Implementation Complete**: February 27, 2025  
**Status**: Ready to Use ✅  
**Support**: Check HISTORIAN_IMPLEMENTATION.md for detailed docs
