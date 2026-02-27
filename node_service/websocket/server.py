"""
WebSocket Server for Node Telemetry Streaming
Broadcasts live telemetry to connected clients (admin and dashboards)
"""

import asyncio
import logging
import json
from typing import Set, Optional, Callable
from datetime import datetime

import websockets
from websockets.server import WebSocketServerProtocol, serve

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket server for streaming telemetry data
    Clients connect and receive live telemetry updates every second
    """
    
    def __init__(self, node_id: str, port: int, get_state_callback: Callable):
        """
        Initialize WebSocket server
        
        Args:
            node_id: Node identifier
            port: WebSocket server port
            get_state_callback: Async function to get current node state
        """
        self.node_id = node_id
        self.port = port
        self.get_state_callback = get_state_callback
        
        # Connected clients
        self.clients: Set[WebSocketServerProtocol] = set()
        
        # Server instance
        self._server: Optional[websockets.WebSocketServer] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"WebSocket server initialized for {node_id} on port {port}")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle a new WebSocket client connection
        
        Args:
            websocket: WebSocket connection
            path: Request path
        """
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"WebSocket client connected: {client_id} -> {path}")
        
        # Add client to set
        self.clients.add(websocket)
        
        try:
            # Send initial state
            state = await self.get_state_callback()
            if state:
                await websocket.send(json.dumps({
                    'type': 'telemetry',
                    'data': state
                }))
            
            # Keep connection alive and handle incoming messages
            async for message in websocket:
                # Handle client messages (e.g., subscription requests)
                try:
                    data = json.loads(message)
                    logger.debug(f"Received from {client_id}: {data}")
                    
                    # Echo acknowledgment
                    await websocket.send(json.dumps({
                        'type': 'ack',
                        'message': 'Message received'
                    }))
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {client_id}: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket client disconnected: {client_id}")
        
        except Exception as e:
            logger.error(f"Error handling WebSocket client {client_id}: {e}", exc_info=True)
        
        finally:
            # Remove client from set
            self.clients.discard(websocket)
    
    async def broadcast_telemetry(self):
        """
        Broadcast telemetry to all connected clients periodically
        Runs every second
        """
        logger.info(f"Starting telemetry broadcast for {self.node_id}")
        
        while self._running:
            try:
                if self.clients:
                    # Get current state
                    state = await self.get_state_callback()
                    
                    if state:
                        message = json.dumps({
                            'type': 'telemetry',
                            'timestamp': datetime.utcnow().isoformat(),
                            'data': state
                        })
                        
                        # Broadcast to all connected clients
                        websockets_to_remove = set()
                        for client in self.clients:
                            try:
                                await client.send(message)
                            except websockets.exceptions.ConnectionClosed:
                                websockets_to_remove.add(client)
                            except Exception as e:
                                logger.error(f"Error sending to client: {e}")
                                websockets_to_remove.add(client)
                        
                        # Remove dead connections
                        self.clients -= websockets_to_remove
                
                # Broadcast every 1 second
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)
    
    async def start(self):
        """Start the WebSocket server"""
        if self._running:
            logger.warning(f"WebSocket server already running on port {self.port}")
            return
        
        self._running = True
        
        # Start WebSocket server
        logger.info(f"Starting WebSocket server on 0.0.0.0:{self.port}")
        
        try:
            self._server = await serve(
                self.handle_client,
                "0.0.0.0",
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Start broadcast task
            self._broadcast_task = asyncio.create_task(self.broadcast_telemetry())
            
            logger.info(f"✅ WebSocket server started on port {self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}", exc_info=True)
            self._running = False
            raise
    
    async def stop(self):
        """Stop the WebSocket server"""
        if not self._running:
            return
        
        logger.info(f"Stopping WebSocket server on port {self.port}")
        self._running = False
        
        # Stop broadcast task
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
            self.clients.clear()
        
        # Stop server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        logger.info(f"WebSocket server stopped")
    
    def get_stats(self) -> dict:
        """Get server statistics"""
        return {
            'node_id': self.node_id,
            'port': self.port,
            'running': self._running,
            'connected_clients': len(self.clients),
            'client_addresses': [
                f"{ws.remote_address[0]}:{ws.remote_address[1]}"
                for ws in self.clients
            ]
        }
