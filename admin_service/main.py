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

from config import AdminConfig
from master import NodeRegistry, NodeConnector, TelemetryAggregator
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
        
        # Heartbeat check task
        self._heartbeat_task: Optional[asyncio.Task] = None
        
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
    
    async def start_all_services(self):
        """Start all admin services"""
        logger.info("Starting all admin services")
        
        # Start WebSocket manager
        await self.ws_manager.start()
        
        # Start node connector (will connect to registered nodes)
        await self.connector.start_all()
        
        # Start heartbeat monitor
        self._heartbeat_task = asyncio.create_task(self.heartbeat_monitor())
        
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
