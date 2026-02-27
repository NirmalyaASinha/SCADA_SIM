#!/bin/bash

clear
echo "╔══════════════════════════════════════════╗"
echo "║   SCADA PLATFORM -- FULL SYSTEM LAUNCH   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

echo "🔨 Building Docker images..."
docker compose build

echo ""
echo "🚀 Starting infrastructure services..."
docker compose up -d timescaledb redis prometheus grafana

echo "⏳ Waiting for database to be ready..."
sleep 10

echo ""
echo "🚀 Starting admin service..."
docker compose up -d admin_service

echo "⏳ Waiting for admin service to initialize..."
sleep 5

echo ""
echo "🚀 Starting 7 node services..."
docker compose up -d \
    node_gen001 node_gen002 \
    node_sub001 node_sub002 node_sub003 \
    node_dist001 node_dist002

echo "⏳ Waiting for all services to stabilize..."
sleep 8

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    SYSTEM OPERATIONAL                             ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                   ║"
echo "║  📊 ADMIN DASHBOARD  →  http://localhost:3000                     ║"
echo "║     Login            →  admin / Admin@SCADA                       ║"
echo "║                                                                   ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                   ║"
echo "║  🎛️  NODE OPERATOR DASHBOARDS:                                    ║"
echo "║     GEN-001  →  http://localhost:8101/ui                          ║"
echo "║     GEN-002  →  http://localhost:8103/ui                          ║"
echo "║     SUB-001  →  http://localhost:8111/ui                          ║"
echo "║     SUB-002  →  http://localhost:8113/ui                          ║"
echo "║     SUB-003  →  http://localhost:8115/ui                          ║"
echo "║     DIST-001 →  http://localhost:8131/ui                          ║"
echo "║     DIST-002 →  http://localhost:8133/ui                          ║"
echo "║                                                                   ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                   ║"
echo "║  🔌 MODBUS TCP PORTS (no authentication - S7-200 legacy):         ║"
echo "║     GEN-001  →  localhost:5020  (Unit ID: 1)                      ║"
echo "║     GEN-002  →  localhost:5021  (Unit ID: 2)                      ║"
echo "║     SUB-001  →  localhost:5030  (Unit ID: 3)                      ║"
echo "║     SUB-002  →  localhost:5031  (Unit ID: 4)                      ║"
echo "║     SUB-003  →  localhost:5032  (Unit ID: 5)                      ║"
echo "║     DIST-001 →  localhost:5040  (Unit ID: 6)                      ║"
echo "║     DIST-002 →  localhost:5041  (Unit ID: 7)                      ║"
echo "║                                                                   ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                   ║"
echo "║  📈 MONITORING:                                                   ║"
echo "║     Grafana     →  http://localhost:3001  (admin / admin123)      ║"
echo "║     Prometheus  →  http://localhost:9090                          ║"
echo "║                                                                   ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                   ║"
echo "║  📝 NODE OPERATOR CREDENTIALS:                                    ║"
echo "║     GEN-001  →  operator_gen001 / Login@SCADA                     ║"
echo "║     GEN-002  →  operator_gen002 / Login@SCADA                     ║"
echo "║     SUB-001  →  operator_sub001 / Login@SCADA                     ║"
echo "║     SUB-002  →  operator_sub002 / Login@SCADA                     ║"
echo "║     SUB-003  →  operator_sub003 / Login@SCADA                     ║"
echo "║     DIST-001 →  operator_dist001 / Login@SCADA                    ║"
echo "║     DIST-002 →  operator_dist002 / Login@SCADA                    ║"
echo "║                                                                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Get and display local IP for cross-machine access
echo "🌐 Your IP address (for cross-machine access):"
if command -v hostname &> /dev/null; then
    hostname -I | awk '{print "   → "$1}' 2>/dev/null || ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print "   → "$2}' | head -1
fi

echo ""
echo "✅ All services started successfully!"
echo ""
echo "📌 To view logs: ./logs.sh"
echo "📌 To stop all services: ./stop.sh"
echo "📌 To check status: ./status.sh"
echo ""
