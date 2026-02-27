"""
Node Connector
Maintains WebSocket connections to all registered nodes
Receives live telemetry streams
"""

import asyncio
import logging
import json
from typing import Dict, Optional, Callable
from datetime import datetime

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class NodeConnector:
    """
    Manages WebSocket connections to all SCADA nodes
    Admin connects TO nodes (pull model)
    """
    
    def __init__(self, registry, telemetry_callback: Callable):
        """
        Initialize node connector
        
        Args:
            registry: NodeRegistry instance
            telemetry_callback: Async function called with (node_id, telemetry_data)
        """
        self.registry = registry
        self.telemetry_callback = telemetry_callback
        
        # Active connections: node_id -> websocket
        self.connections: Dict[str, WebSocketClientProtocol] = {}
        
        # Connection tasks
        self.connection_tasks: Dict[str, asyncio.Task] = {}
        
        # Running flag
        self._running = False
        
        logger.info("Node connector initialized")
    
    async def connect_to_node(self, node_id: str, node_info: Dict):
        """
        Establish WebSocket connection to a node
        
        Args:
            node_id: Node identifier
            node_info: Node registration info
        """
        ws_url = f"ws://{node_info['ip']}:{node_info['ws_port']}/ws/telemetry"
        retry_delay = 5  # seconds
        
        logger.info(f"Connecting to {node_id} at {ws_url}")
        
        while self._running:
            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    logger.info(f"✅ Connected to {node_id}")
                    self.connections[node_id] = websocket
                    
                    # Update node status
                    self.registry.update_node_status(node_id, 'ONLINE')
                    
                    # Receive telemetry messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            
                            # Process telemetry message
                            if data.get('type') == 'telemetry':
                                await self.telemetry_callback(node_id, data.get('data', {}))
                        
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from {node_id}: {message}")
                        except Exception as e:
                            logger.error(f"Error processing message from {node_id}: {e}")
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Connection to {node_id} closed")
            
            except Exception as e:
                logger.error(f"Error connecting to {node_id}: {e}")
            
            finally:
                # Remove from active connections
                if node_id in self.connections:
                    del self.connections[node_id]
                
                # Update node status
                self.registry.update_node_status(node_id, 'DEGRADED')
            
            # Retry connection
            if self._running:
                logger.info(f"Retrying connection to {node_id} in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
    
    async def start_connection(self, node_id: str):
        """
        Start connection to a node
        
        Args:
            node_id: Node identifier
        """
        if node_id in self.connection_tasks:
            logger.warning(f"Connection task already exists for {node_id}")
            return
        
        node_info = self.registry.get_node(node_id)
        if not node_info:
            logger.error(f"Cannot connect to unregistered node: {node_id}")
            return
        
        # Create connection task
        task = asyncio.create_task(self.connect_to_node(node_id, node_info))
        self.connection_tasks[node_id] = task
        
        logger.info(f"Started connection task for {node_id}")
    
    async def stop_connection(self, node_id: str):
        """
        Stop connection to a node
        
        Args:
            node_id: Node identifier
        """
        # Close WebSocket connection
        if node_id in self.connections:
            try:
                await self.connections[node_id].close()
            except:
                pass
            del self.connections[node_id]
        
        # Cancel connection task
        if node_id in self.connection_tasks:
            self.connection_tasks[node_id].cancel()
            try:
                await self.connection_tasks[node_id]
            except asyncio.CancelledError:
                pass
            del self.connection_tasks[node_id]
        
        logger.info(f"Stopped connection to {node_id}")
    
    async def start_all(self):
        """Start connections to all registered nodes"""
        self._running = True
        
        for node_id in self.registry.nodes.keys():
            await self.start_connection(node_id)
        
        logger.info("Started all node connections")
    
    async def stop_all(self):
        """Stop all node connections"""
        self._running = False
        
        # Stop all connections
        for node_id in list(self.connection_tasks.keys()):
            await self.stop_connection(node_id)
        
        logger.info("Stopped all node connections")
    
    def get_connection_status(self) -> Dict[str, str]:
        """Get connection status for all nodes"""
        return {
            node_id: 'CONNECTED' if node_id in self.connections else 'DISCONNECTED'
            for node_id in self.registry.nodes.keys()
        }
    
    def is_connected(self, node_id: str) -> bool:
        """Check if connected to a node"""
        return node_id in self.connections
