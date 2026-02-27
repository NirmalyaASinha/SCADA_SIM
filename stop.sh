#!/bin/bash

echo "🛑 Stopping all SCADA services..."

docker compose down

echo ""
echo "✅ All services stopped."
echo ""
echo "💡 To remove volumes (clean database): docker compose down -v"
