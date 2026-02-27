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
if netstat -tuln 2>/dev/null | grep -q ":9001 " || ss -tuln 2>/dev/null | grep -q ":9001 "; then
    echo "✅ Admin WebSocket  "
else
    echo "❌ Admin WebSocket   (not listening)"
fi
check_health "Admin Dashboard  " 3000 "/"
echo ""

# Node Services
echo "━━━ NODE SERVICES ━━━"
check_health "GEN-001 REST     " 8101 "/health"
check_health "GEN-001 Dashboard" 8101 "/ui"
if netstat -tuln 2>/dev/null | grep -q ":8102 " || ss -tuln 2>/dev/null | grep -q ":8102 "; then
    echo "✅ GEN-001 WebSocket"
else
    echo "❌ GEN-001 WebSocket (not listening)"
fi
echo ""

check_health "GEN-002 REST     " 8103 "/health"
check_health "GEN-002 Dashboard" 8103 "/ui"
if netstat -tuln 2>/dev/null | grep -q ":8104 " || ss -tuln 2>/dev/null | grep -q ":8104 "; then
    echo "✅ GEN-002 WebSocket"
else
    echo "❌ GEN-002 WebSocket (not listening)"
fi
echo ""

check_health "SUB-001 REST     " 8111 "/health"
check_health "SUB-001 Dashboard" 8111 "/ui"
if netstat -tuln 2>/dev/null | grep -q ":8112 " || ss -tuln 2>/dev/null | grep -q ":8112 "; then
    echo "✅ SUB-001 WebSocket"
else
    echo "❌ SUB-001 WebSocket (not listening)"
fi
echo ""

check_health "SUB-002 REST     " 8113 "/health"
check_health "SUB-002 Dashboard" 8113 "/ui"
if netstat -tuln 2>/dev/null | grep -q ":8114 " || ss -tuln 2>/dev/null | grep -q ":8114 "; then
    echo "✅ SUB-002 WebSocket"
else
    echo "❌ SUB-002 WebSocket (not listening)"
fi
echo ""

check_health "SUB-003 REST     " 8115 "/health"
check_health "SUB-003 Dashboard" 8115 "/ui"
if netstat -tuln 2>/dev/null | grep -q ":8116 " || ss -tuln 2>/dev/null | grep -q ":8116 "; then
    echo "✅ SUB-003 WebSocket"
else
    echo "❌ SUB-003 WebSocket (not listening)"
fi
echo ""

check_health "DIST-001 REST    " 8131 "/health"
check_health "DIST-001 Dashboard" 8131 "/ui"
if netstat -tuln 2>/dev/null | grep -q ":8132 " || ss -tuln 2>/dev/null | grep -q ":8132 "; then
    echo "✅ DIST-001 WebSocket"
else
    echo "❌ DIST-001 WebSocket (not listening)"
fi
echo ""

check_health "DIST-002 REST    " 8133 "/health"
check_health "DIST-002 Dashboard" 8133 "/ui"
if netstat -tuln 2>/dev/null | grep -q ":8134 " || ss -tuln 2>/dev/null | grep -q ":8134 "; then
    echo "✅ DIST-002 WebSocket"
else
    echo "❌ DIST-002 WebSocket (not listening)"
fi
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
