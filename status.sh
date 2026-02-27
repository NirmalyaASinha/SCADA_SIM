#!/bin/bash

echo "╔═══════════════════════════════════════════╗"
echo "║   SCADA PLATFORM -- SERVICE STATUS        ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Check if any containers are running
if ! docker compose ps --services --filter "status=running" 2>/dev/null | grep -q .; then
    echo "❌ No services running"
    echo ""
    echo "Start services with: ./launch.sh"
    exit 1
fi

echo "🔍 Checking service health..."
echo ""

# Health check function
check_health() {
    local name=$1
    local port=$2
    local endpoint=$3
    
    if curl -s -f -m 2 "http://localhost:$port$endpoint" > /dev/null 2>&1; then
        echo "✅ $name"
    else
        echo "❌ $name (not responding)"
    fi
}

# Infrastructure
echo "━━━ INFRASTRUCTURE ━━━"
check_health "TimescaleDB      " 5432 "/"  # Will fail but container should be up
if docker compose ps timescaledb 2>/dev/null | grep -q "Up"; then
    echo "✅ TimescaleDB       (container running)"
else
    echo "❌ TimescaleDB       (container not running)"
fi

if docker compose ps redis 2>/dev/null | grep -q "Up"; then
    echo "✅ Redis             (container running)"
else
    echo "❌ Redis             (container not running)"
fi
echo ""

# Admin Service
echo "━━━ ADMIN SERVICE ━━━"
check_health "Admin REST API   " 9000 "/health"
check_health "Admin WebSocket  " 9001 "/"  # Will fail WebSocket on HTTP but checks port
check_health "Admin Dashboard  " 3000 "/"
echo ""

# Node Services
echo "━━━ NODE SERVICES ━━━"
check_health "GEN-001 REST     " 8101 "/health"
check_health "GEN-001 Dashboard" 8101 "/ui"
check_health "GEN-001 WebSocket" 8102 "/"
echo ""

check_health "GEN-002 REST     " 8103 "/health"
check_health "GEN-002 Dashboard" 8103 "/ui"
check_health "GEN-002 WebSocket" 8104 "/"
echo ""

check_health "SUB-001 REST     " 8111 "/health"
check_health "SUB-001 Dashboard" 8111 "/ui"
check_health "SUB-001 WebSocket" 8112 "/"
echo ""

check_health "SUB-002 REST     " 8113 "/health"
check_health "SUB-002 Dashboard" 8113 "/ui"
check_health "SUB-002 WebSocket" 8114 "/"
echo ""

check_health "SUB-003 REST     " 8115 "/health"
check_health "SUB-003 Dashboard" 8115 "/ui"
check_health "SUB-003 WebSocket" 8116 "/"
echo ""

check_health "DIST-001 REST    " 8131 "/health"
check_health "DIST-001 Dashboard" 8131 "/ui"
check_health "DIST-001 WebSocket" 8132 "/"
echo ""

check_health "DIST-002 REST    " 8133 "/health"
check_health "DIST-002 Dashboard" 8133 "/ui"
check_health "DIST-002 WebSocket" 8134 "/"
echo ""

# Monitoring
echo "━━━ MONITORING ━━━"
check_health "Prometheus       " 9090 "/-/healthy"
check_health "Grafana          " 3001 "/api/health"
echo ""

# Modbus ports (can't easily check without Modbus client)
echo "━━━ MODBUS TCP PORTS (listening) ━━━"
for port in 5020 5021 5030 5031 5032 5040 5041; do
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        echo "✅ Port $port (listening)"
    else
        echo "❌ Port $port (not listening)"
    fi
done
echo ""

# Container summary
echo "━━━ DOCKER CONTAINERS ━━━"
docker compose ps
echo ""

echo "💡 View real-time logs: ./logs.sh"
echo "💡 Stop all services: ./stop.sh"
