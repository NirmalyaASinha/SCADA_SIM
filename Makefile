.PHONY: help start stop restart status logs clean build node

help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║          SCADA Platform - Makefile Commands                   ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  make start          - Start full system (alias for ./launch.sh)"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make status         - Check service health"
	@echo "  make logs           - View combined logs"
	@echo "  make logs-admin     - View admin service logs"
	@echo "  make logs-gen1      - View GEN-001 logs"
	@echo "  make logs-sub1      - View SUB-001 logs"
	@echo "  make build          - Build all Docker images"
	@echo "  make clean          - Stop and remove all containers + volumes"
	@echo "  make node NODE=SUB-001  - Start specific node on remote machine"
	@echo ""
	@echo "Examples:"
	@echo "  make start"
	@echo "  make logs-admin"
	@echo "  make node NODE=SUB-001"
	@echo ""

start:
	./launch.sh

stop:
	./stop.sh

restart: stop start

status:
	./status.sh

logs:
	docker compose logs -f --tail=50

logs-admin:
	docker compose logs -f --tail=100 admin_service

logs-gen1:
	docker compose logs -f --tail=100 node_gen001

logs-gen2:
	docker compose logs -f --tail=100 node_gen002

logs-sub1:
	docker compose logs -f --tail=100 node_sub001

logs-sub2:
	docker compose logs -f --tail=100 node_sub002

logs-sub3:
	docker compose logs -f --tail=100 node_sub003

logs-dist1:
	docker compose logs -f --tail=100 node_dist001

logs-dist2:
	docker compose logs -f --tail=100 node_dist002

build:
	docker compose build

clean:
	@echo "⚠️  WARNING: This will delete all containers and data volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		echo "✅ All containers and volumes removed"; \
	else \
		echo "❌ Cancelled"; \
	fi

node:
ifndef NODE
	@echo "❌ Error: NODE parameter required"
	@echo "Usage: make node NODE=SUB-001"
	@exit 1
endif
	./launch_node.sh $(NODE)

# Database shortcuts
db-shell:
	docker exec -it scada_timescaledb psql -U scada_admin -d scada_platform

db-backup:
	docker exec scada_timescaledb pg_dump -U scada_admin scada_platform > backup_$(shell date +%Y%m%d_%H%M%S).sql

db-restore:
ifndef FILE
	@echo "❌ Error: FILE parameter required"
	@echo "Usage: make db-restore FILE=backup_20240101_120000.sql"
	@exit 1
endif
	docker exec -i scada_timescaledb psql -U scada_admin scada_platform < $(FILE)
