"""
SCADA Admin Service Main Entry Point
Central master service for SCADA network
"""

import asyncio
import logging
import sys
import time
from typing import Dict, Optional

import uvicorn
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from config import AdminConfig
from master import NodeRegistry, NodeConnector, TelemetryAggregator, PowerFlowEngine
from websocket import AdminWebSocketManager
from api import create_admin_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('admin_service.log')
    ]
)
logger = logging.getLogger(__name__)


class AdminService:
    """
    Main admin service orchestrator
    Manages node registry, connections, and aggregation
    """
    
    def __init__(self, config: AdminConfig):
        self.config = config
        self.start_time = time.time()
        
        # Create registry
        self.registry = NodeRegistry()
        
        # Create telemetry aggregator
        self.aggregator = TelemetryAggregator()

        # Create power flow engine
        self.power_flow = PowerFlowEngine()
        self.power_flow_edges = []
        
        # Create node connector
        self.connector = NodeConnector(
            registry=self.registry,
            telemetry_callback=self._on_telemetry_received
        )
        
        # Create admin WebSocket manager
        self.ws_manager = AdminWebSocketManager(
            port=9001,  # Admin WebSocket port
            aggregator=self.aggregator
        )

        # Database engine (if available)
        self.db_engine = None
        try:
            db_url_async = config.DB_URL.replace('postgresql://', 'postgresql+asyncpg://')
            self.db_engine = create_async_engine(db_url_async, echo=False)
            logger.info("Admin database engine initialized")
        except Exception as e:
            logger.warning(f"Database not available: {e}")
        
        # Heartbeat check task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._power_flow_task: Optional[asyncio.Task] = None
        
        logger.info("AdminService initialized")
    
    async def _on_telemetry_received(self, node_id: str, telemetry: Dict):
        """
        Callback when telemetry is received from a node
        
        Args:
            node_id: Node identifier
            telemetry: Telemetry data dictionary
        """
        # Update aggregator
        self.aggregator.update_telemetry(node_id, telemetry)
    
    async def heartbeat_monitor(self):
        """Monitor node heartbeats periodically"""
        logger.info("Starting heartbeat monitor")
        
        while True:
            try:
                # Check heartbeats every 15 seconds
                await asyncio.sleep(15)
                
                # Check all node heartbeats
                self.registry.check_heartbeats()
            
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}", exc_info=True)

    async def _collect_node_states(self) -> Dict[str, str]:
        """Build a normalized node state map from telemetry and registry"""
        node_states: Dict[str, str] = {}

        latest = self.aggregator.get_all_latest()
        for node_id, telemetry in latest.items():
            state = telemetry.get('node_state') or telemetry.get('operational_state') or 'UNKNOWN'
            node_states[node_id] = state

        for node_id, node_info in self.registry.nodes.items():
            if node_info.get('status') == 'OFFLINE':
                node_states[node_id] = 'OFFLINE'

        return node_states

    async def _refresh_power_flow(self):
        """Recompute energized edges for the topology map"""
        node_states = await self._collect_node_states()
        telemetry = self.aggregator.get_all_latest()
        self.power_flow_edges = await self.power_flow.get_energized_edges(node_states, telemetry)

    async def power_flow_loop(self):
        """Periodic power flow update loop"""
        logger.info("Starting power flow engine loop")

        while True:
            try:
                await asyncio.sleep(2)
                await self._refresh_power_flow()
            except Exception as e:
                logger.error(f"Error in power flow loop: {e}", exc_info=True)

    async def log_cascade_event(self, event: Dict):
        """Persist cascade event to the database"""
        if self.db_engine is None:
            return

        try:
            async with self.db_engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO cascade_events (
                            trigger_node,
                            trigger_state,
                            trigger_reason,
                            trigger_operator,
                            affected_nodes,
                            households_affected,
                            severity
                        )
                        VALUES (
                            :trigger_node,
                            :trigger_state,
                            :trigger_reason,
                            :trigger_operator,
                            :affected_nodes,
                            :households_affected,
                            :severity
                        )
                        """
                    ),
                    {
                        'trigger_node': event.get('trigger_node'),
                        'trigger_state': event.get('trigger_state'),
                        'trigger_reason': event.get('trigger_reason'),
                        'trigger_operator': event.get('trigger_operator'),
                        'affected_nodes': event.get('affected_nodes', []),
                        'households_affected': event.get('households_affected', 0),
                        'severity': event.get('severity', 'CRITICAL')
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log cascade event: {e}")

    async def log_cascade_restoration(self, trigger_node: str):
        """Update the latest cascade event when power is restored"""
        if self.db_engine is None:
            return

        try:
            async with self.db_engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        WITH latest AS (
                            SELECT id
                            FROM cascade_events
                            WHERE trigger_node = :trigger_node
                              AND restored_at IS NULL
                            ORDER BY timestamp DESC
                            LIMIT 1
                        )
                        UPDATE cascade_events
                        SET restored_at = NOW(),
                            duration_seconds = EXTRACT(EPOCH FROM (NOW() - timestamp))::INTEGER
                        WHERE id IN (SELECT id FROM latest)
                        """
                    ),
                    {'trigger_node': trigger_node}
                )
        except Exception as e:
            logger.error(f"Failed to update cascade restoration: {e}")
    
    async def start_all_services(self):
        """Start all admin services"""
        logger.info("Starting all admin services")
        
        # Start WebSocket manager
        await self.ws_manager.start()
        
        # Start node connector (will connect to registered nodes)
        await self.connector.start_all()
        
        # Start heartbeat monitor
        self._heartbeat_task = asyncio.create_task(self.heartbeat_monitor())

        # Start power flow engine
        self._power_flow_task = asyncio.create_task(self.power_flow_loop())
        
        logger.info("✅ All admin services started")
        self._print_startup_summary()
    
    def _print_startup_summary(self):
        """Print startup summary"""
        print()
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║   SCADA MASTER OPERATIONAL                                ║")
        print("╠═══════════════════════════════════════════════════════════╣")
        print(f"║  Master API     : http://0.0.0.0:{self.config.API_PORT}                  ║")
        print(f"║  Admin Dashboard: http://0.0.0.0:3000                      ║")
        print(f"║  WebSocket      : ws://0.0.0.0:9001                        ║")
        print("╠═══════════════════════════════════════════════════════════╣")
        print(f"║  Default Admin Login:                                     ║")
        print(f"║    Username: admin                                        ║")
        print(f"║    Password: admin@scada2024                              ║")
        print("║                                                           ║")
        print(f"║  Engineer Login:                                          ║")
        print(f"║    Username: engineer                                     ║")
        print(f"║    Password: eng@scada2024                                ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()


async def main():
    """Main entry point"""
    # Load configuration
    config = AdminConfig()
    logger.info(f"Configuration loaded:\n{config}")
    
    # Create admin service
    admin_service = AdminService(config)
    
    # Start all services
    await admin_service.start_all_services()
    
    # Create FastAPI app
    api_app = create_admin_app(admin_service)
    
    # Create uvicorn servers for both API and Dashboard ports
    api_config = uvicorn.Config(
        api_app,
        host="0.0.0.0",
        port=config.API_PORT,
        log_level="info",
        access_log=True
    )
    dashboard_config = uvicorn.Config(
        api_app,
        host="0.0.0.0",
        port=config.DASHBOARD_PORT,
        log_level="info",
        access_log=False
    )
    
    api_server = uvicorn.Server(api_config)
    dashboard_server = uvicorn.Server(dashboard_config)
    
    # Run both servers concurrently
    await asyncio.gather(
        api_server.serve(),
        dashboard_server.serve()
    )


if __name__ == "__main__":
    asyncio.run(main())
