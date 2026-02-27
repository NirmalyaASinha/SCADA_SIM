#!/bin/bash

# Launch a single node on a remote machine
# Usage: ./launch_node.sh [NODE_ID]
# Example: ./launch_node.sh SUB-001

clear
echo "╔═══════════════════════════════════════╗"
echo "║   SCADA NODE -- STANDALONE LAUNCHER   ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check if node ID is provided
if [ -z "$1" ]; then
    echo "❌ Error: Node ID required"
    echo ""
    echo "Usage: ./launch_node.sh [NODE_ID]"
    echo ""
    echo "Available nodes:"
    echo "  • GEN-001  (Generation Station 1)"
    echo "  • GEN-002  (Generation Station 2)"
    echo "  • SUB-001  (Transmission Substation 1)"
    echo "  • SUB-002  (Transmission Substation 2)"
    echo "  • SUB-003  (Transmission Substation 3)"
    echo "  • DIST-001 (Distribution Station 1)"
    echo "  • DIST-002 (Distribution Station 2)"
    echo ""
    echo "Example: ./launch_node.sh SUB-001"
    exit 1
fi

NODE_ID=$1

# Validate node ID
case "$NODE_ID" in
    GEN-001|GEN-002|SUB-001|SUB-002|SUB-003|DIST-001|DIST-002)
        ;;
    *)
        echo "❌ Invalid node ID: $NODE_ID"
        echo "Valid IDs: GEN-001, GEN-002, SUB-001, SUB-002, SUB-003, DIST-001, DIST-002"
        exit 1
        ;;
esac

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Map node ID to service name
SERVICE_NAME=$(echo "$NODE_ID" | tr '[:upper:]' '[:lower:]' | tr '-' '_' | sed 's/^/node_/')

echo "🔨 Building Docker image for $NODE_ID..."
docker compose -f docker-compose.nodes.yml build $SERVICE_NAME

echo ""
echo "🚀 Starting node $NODE_ID..."
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  The startup dialog will ask for the Master (Admin) IP address   ║"
echo "║                                                                   ║"
echo "║  ▶ If the admin is on THIS machine:                              ║"
echo "║    Enter: localhost                                               ║"
echo "║                                                                   ║"
echo "║  ▶ If the admin is on ANOTHER machine (same network):            ║"
echo "║    - Find the admin machine's IP with: hostname -I                ║"
echo "║    - Enter that IP (e.g., 192.168.1.100)                          ║"
echo "║                                                                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
read -p "Press ENTER to continue..."
echo ""

# Run with interactive mode
docker compose -f docker-compose.nodes.yml run --rm --service-ports $SERVICE_NAME

echo ""
echo "✅ Node stopped."
