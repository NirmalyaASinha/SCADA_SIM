# Troubleshooting Guide

## Services Won't Start

```bash
# Verify Docker is running
docker info

# View error logs for all services
./logs.sh

# Clean restart (preserves database)
./stop.sh
./launch.sh

# Full clean restart (WARNING: deletes all database data)
./stop.sh
docker compose down -v
./launch.sh
```

---

## Node Can't Connect to Admin (Cross-Machine Deployment)

```bash
# On the admin machine — check firewall
sudo ufw status
sudo ufw allow 9000/tcp   # Admin REST API
sudo ufw allow 9001/tcp   # Admin WebSocket

# On the node machine — verify connectivity
curl http://<admin-ip>:9000/health

# Confirm the admin machine IP
hostname -I   # Run on admin machine
```

---

## Database Connection Errors

```bash
# Give the database more time to initialize
docker compose up -d timescaledb
sleep 15
docker compose up -d admin_service

# Check database logs
docker logs scada_timescaledb

# Connect directly to verify
docker exec -it scada_timescaledb psql -U scada -d scadadb -c "\dt"
```

---

## Port Conflicts

```bash
# Find what is using a port
sudo netstat -tulpn | grep 8101

# Change ports via environment variables
# Edit .env (copy from .env.example):
GEN001_REST_PORT=8201    # Changed from 8101
```

---

## Dashboard Not Loading

- Ensure the admin service is running: `./status.sh`
- Check CDN availability (jsDelivr is used for React). If offline, the UI may not load.
- Try a hard refresh (`Ctrl+Shift+R`) to clear cached assets.

---

## Historian / Chart Shows No Data

```bash
# Verify data is being written to the database
docker exec -it scada_timescaledb psql -U scada -d scadadb \
  -c "SELECT count(*) FROM node_telemetry WHERE timestamp > NOW() - INTERVAL '5 minutes';"
```

If the count is 0, check node and admin service logs:
```bash
./logs.sh admin_service
./logs.sh node_gen001
```

---

## Useful Debug Commands

```bash
# Status of all services
./status.sh

# Logs for a specific service
./logs.sh admin_service
./logs.sh node_gen001

# Check which containers are running
docker compose ps

# Restart a single service
docker compose restart admin_service
```
