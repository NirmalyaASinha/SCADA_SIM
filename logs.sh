#!/bin/bash

clear
echo "╔════════════════════════════════════════╗"
echo "║   SCADA PLATFORM -- SERVICE LOGS       ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if service name is provided
if [ -z "$1" ]; then
    echo "📋 Available services:"
    echo ""
    echo "  Infrastructure:"
    echo "    • timescaledb"
    echo "    • redis"
    echo "    • prometheus"
    echo "    • grafana"
    echo ""
    echo "  Admin:"
    echo "    • admin_service"
    echo ""
    echo "  Nodes:"
    echo "    • node_gen001"
    echo "    • node_gen002"
    echo "    • node_sub001"
    echo "    • node_sub002"
    echo "    • node_sub003"
    echo "    • node_dist001"
    echo "    • node_dist002"
    echo ""
    echo "Usage:"
    echo "  ./logs.sh [service]    - Follow logs for specific service"
    echo "  ./logs.sh              - Follow all services (combined)"
    echo ""
    echo "Examples:"
    echo "  ./logs.sh admin_service"
    echo "  ./logs.sh node_gen001"
    echo ""
    read -p "Press ENTER to view all logs, or Ctrl+C to cancel..."
    echo ""
    docker compose logs -f --tail=50
else
    echo "📡 Following logs for: $1"
    echo "   (Press Ctrl+C to exit)"
    echo ""
    docker compose logs -f --tail=100 "$1"
fi
