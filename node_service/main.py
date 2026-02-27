"""
SCADA Node Service Main Entry Point
Coordinates simulation, Modbus server, REST API, WebSocket, and master registration
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

import uvicorn
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import httpx

from config import NodeConfig
from startup_dialog import run_startup_dialog
from simulation import GenerationNode, SubstationNode, DistributionNode
from protocols import ModbusServer
from websocket import WebSocketServer
from api import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('node_service.log')
    ]
)
logger = logging.getLogger(__name__)


class NodeService:
    """
    Main node service orchestrator
    Manages all components of a SCADA node
    """
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.start_time = time.time()
        
        # Create simulation node based on type
        if config.NODE_TYPE == 'generation':
            self.simulation = GenerationNode(config.NODE_ID, {})
        elif config.NODE_TYPE == 'transmission':
            self.simulation = SubstationNode(config.NODE_ID, {})
        elif config.NODE_TYPE == 'distribution':
            self.simulation = DistributionNode(config.NODE_ID, {})
        else:
            raise ValueError(f"Unknown node type: {config.NODE_TYPE}")
        
        # Create Modbus server
        self.modbus_server = ModbusServer(
            node_id=config.NODE_ID,
            unit_id=config.UNIT_ID,
            port=config.MODBUS_PORT,
            update_callback=self._get_simulation_state,
            log_callback=self._log_modbus_transaction
        )
        
        # Create WebSocket server
        self.ws_server = WebSocketServer(
            node_id=config.NODE_ID,
            port=config.WS_PORT,
            get_state_callback=self._get_simulation_state
        )
        
        # Database engine (if available)
        self.db_engine = None
        try:
            # Convert PostgreSQL URL for asyncpg
            db_url_async = config.DB_URL.replace('postgresql://', 'postgresql+asyncpg://')
            self.db_engine = create_async_engine(db_url_async, echo=False)
            logger.info("Database engine initialized")
        except Exception as e:
            logger.warning(f"Database not available: {e}")
        
        # HTTP client for master communication
        self.http_client = httpx.AsyncClient(timeout=10.0)
        
        # Master registration status
        self.registered_with_master = False
        self.master_reachable = False
        
        # Event log (in-memory, limited size)
        self.event_log = []
        self.max_events = 1000
        
        logger.info(f"NodeService initialized: {config.NODE_ID}")
    
    async def _get_simulation_state(self) -> Dict[str, Any]:
        """Get current simulation state as dictionary"""
        return self.simulation.get_state().to_dict()
    
    def _log_modbus_transaction(
        self,
        node_id: str,
        function_code: int,
        register_address: int,
        value: int,
        direction: str,
        is_write: bool
    ):
        """
        Log Modbus transaction (synchronous callback)
        Offloads to async task for database logging
        """
        asyncio.create_task(self._async_log_modbus_transaction(
            node_id, function_code, register_address, value, direction, is_write
        ))
    
    async def _async_log_modbus_transaction(
        self,
        node_id: str,
        function_code: int,
        register_address: int,
        value: int,
        direction: str,
        is_write: bool
    ):
        """Log Modbus transaction to database"""
        if self.db_engine is None:
            return
        
        try:
            async with self.db_engine.begin() as conn:
                await conn.execute(
                    text("""
                        INSERT INTO modbus_transactions 
                        (node_id, source_ip, function_code, register_address, value, direction, is_write)
                        VALUES (:node_id, :source_ip, :fc, :addr, :value, :dir, :is_write)
                    """),
                    {
                        'node_id': node_id,
                        'source_ip': '0.0.0.0',  # TODO: Get actual source IP
                        'fc': function_code,
                        'addr': register_address,
                        'value': value,
                        'dir': direction,
                        'is_write': is_write
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log Modbus transaction: {e}")
    
    async def log_operator_action(
        self,
        operator: str,
        operator_ip: str,
        action_type: str,
        action_detail: Dict,
        result: str
    ):
        """Log operator action to database"""
        if self.db_engine is None:
            return
        
        try:
            async with self.db_engine.begin() as conn:
                await conn.execute(
                    text("""
                        INSERT INTO operator_actions 
                        (operator, operator_ip, node_id, action_type, action_detail, result)
                        VALUES (:operator, :ip, :node_id, :action_type, :detail::jsonb, :result)
                    """),
                    {
                        'operator': operator,
                        'ip': operator_ip,
                        'node_id': self.config.NODE_ID,
                        'action_type': action_type,
                        'detail': str(action_detail),
                        'result': result
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log operator action: {e}")

    async def notify_state_change(
        self,
        new_state: str,
        breaker: str,
        reason: str,
        operator: str
    ):
        """Notify admin service of a node state change"""
        payload = {
            'node_id': self.config.NODE_ID,
            'new_state': new_state,
            'breaker': breaker,
            'reason': reason,
            'operator': operator,
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            await self.http_client.post(
                f"http://{self.config.MASTER_IP}:{self.config.MASTER_PORT}/nodes/{self.config.NODE_ID}/state_change",
                json=payload,
                timeout=5.0
            )
        except Exception as e:
            logger.error(f"Failed to notify admin of state change: {e}")
    
    async def get_recent_events(self, limit: int = 100):
        """Get recent events from memory"""
        return self.event_log[-limit:]
    
    async def get_audit_log(self, limit: int = 100):
        """Get recent audit entries from database"""
        if self.db_engine is None:
            return []
        
        try:
            async with self.db_engine.connect() as conn:
                result = await conn.execute(
                    text("""
                        SELECT timestamp, operator, operator_ip, action_type, action_detail, result
                        FROM operator_actions
                        WHERE node_id = :node_id
                        ORDER BY timestamp DESC
                        LIMIT :limit
                    """),
                    {'node_id': self.config.NODE_ID, 'limit': limit}
                )
                
                rows = result.fetchall()
                return [
                    {
                        'timestamp': row[0].isoformat(),
                        'operator': row[1],
                        'operator_ip': row[2],
                        'action_type': row[3],
                        'action_detail': row[4],
                        'result': row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []
    
    async def register_with_master(self):
        """
        Register this node with SCADA master
        Maintains heartbeat and handles reconnection
        """
        logger.info(f"Starting master registration service...")
        
        registration_payload = {
            'node_id': self.config.NODE_ID,
            'node_type': self.config.NODE_TYPE,
            'ip': self.config.MY_IP,
            'rest_port': self.config.REST_PORT,
            'modbus_port': self.config.MODBUS_PORT,
            'ws_port': self.config.WS_PORT,
            'version': '1.0.0'
        }
        
        while True:
            try:
                # Attempt registration
                if not self.registered_with_master:
                    logger.info(f"Registering with master at {self.config.MASTER_IP}:{self.config.MASTER_PORT}")
                    
                    response = await self.http_client.post(
                        f"http://{self.config.MASTER_IP}:{self.config.MASTER_PORT}/nodes/register",
                        json=registration_payload,
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        self.registered_with_master = True
                        self.master_reachable = True
                        logger.info(f"✅ Registered with SCADA Master at {self.config.MASTER_IP}:{self.config.MASTER_PORT}")
                    else:
                        logger.warning(f"Registration failed: HTTP {response.status_code}")
                
                # Send heartbeat
                if self.registered_with_master:
                    await self.http_client.post(
                        f"http://{self.config.MASTER_IP}:{self.config.MASTER_PORT}/nodes/{self.config.NODE_ID}/heartbeat",
                        json={
                            'timestamp': datetime.utcnow().isoformat(),
                            'status': 'alive'
                        },
                        timeout=5.0
                    )
                    
                    if not self.master_reachable:
                        logger.info(f"✅ Reconnected to SCADA Master")
                        self.master_reachable = True
                
                # Wait 10 seconds before next heartbeat
                await asyncio.sleep(10)
            
            except Exception as e:
                if self.master_reachable:
                    logger.warning(f"⚠ Master unreachable: {e}. Will retry...")
                    self.master_reachable = False
                self.registered_with_master = False
                await asyncio.sleep(10)
    
    async def start_all_services(self):
        """Start all node services"""
        logger.info(f"Starting all services for {self.config.NODE_ID}")
        
        # Start simulation
        await self.simulation.start()
        
        # Start Modbus server
        await self.modbus_server.start()
        
        # Start WebSocket server
        await self.ws_server.start()
        
        # Start master registration (continues in background)
        asyncio.create_task(self.register_with_master())
        
        logger.info(f"✅ All services started for {self.config.NODE_ID}")
        self._print_startup_summary()
    
    def _print_startup_summary(self):
        """Print startup summary"""
        print()
        print("╔═══════════════════════════════════════════════════════════╗")
        print(f"║   NODE {self.config.NODE_ID:8s} OPERATIONAL                        ║")
        print("╠═══════════════════════════════════════════════════════════╣")
        print(f"║  Type           : {self.config.NODE_TYPE:20s}                 ║")
        print(f"║  Master         : {self.config.MASTER_IP:15s}:{self.config.MASTER_PORT:<5d}              ║")
        print("╠═══════════════════════════════════════════════════════════╣")
        print(f"║  Operator UI    : http://{self.config.MY_IP:15s}:{self.config.REST_PORT}/ui        ║")
        print(f"║  REST API       : http://{self.config.MY_IP:15s}:{self.config.REST_PORT}             ║")
        print(f"║  WebSocket      : ws://{self.config.MY_IP:15s}:{self.config.WS_PORT}               ║")
        print(f"║  Modbus TCP     : {self.config.MY_IP:15s}:{self.config.MODBUS_PORT}               ║")
        print("╠═══════════════════════════════════════════════════════════╣")
        print(f"║  ⚠️  MODBUS: NO AUTHENTICATION (S7-200 legacy mode)       ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()


async def main():
    """Main entry point"""
    # Step 1: Show startup dialog
    node_id = os.getenv('NODE_ID', 'GEN-001')
    master_ip, master_port = run_startup_dialog(node_id)
    
    # Step 2: Load configuration
    config = NodeConfig(master_ip=master_ip, master_port=master_port)
    logger.info(f"Configuration loaded:\n{config}")
    
    # Step 3: Create node service
    node_service = NodeService(config)
    
    # Step 4: Start all services
    await node_service.start_all_services()
    
    # Step 5: Start FastAPI server
    api_app = create_app(node_service)
    
    # Create uvicorn server
    uvicorn_config = uvicorn.Config(
        api_app,
        host="0.0.0.0",
        port=config.REST_PORT,
        log_level="info",
        access_log=True
    )
    server = uvicorn.Server(uvicorn_config)
    
    # Run server
    await server.serve()


if __name__ == "__main__":
    import os
    asyncio.run(main())
