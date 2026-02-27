"""
Admin Service WebSocket Manager
Broadcasts aggerated telemetry to admin dashboard clients
"""

import asyncio
import logging
import json
from typing import Set, Optional
from datetime import datetime

import websockets
from websockets.server import WebSocketServerProtocol, serve

logger = logging.getLogger(__name__)


class AdminWebSocketManager:
    """
    WebSocket server for admin dashboard
    Broadcasts aggregated grid telemetry to connected admins
    """
    
    def __init__(self, port: int, aggregator):
        self.port = port
        self.aggregator = aggregator
        
        # Connected admin dashboards
        self.clients: Set[WebSocketServerProtocol] = set()
        
        # Server instance
        self._server: Optional[websockets.WebSocketServer] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"Admin WebSocket manager initialized on port {port}")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new admin dashboard connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Admin dashboard connected: {client_id}")
        
        self.clients.add(websocket)
        
        try:
            # Send initial grid overview
            overview = self.aggregator.get_grid_overview()
            await websocket.send(json.dumps({
                'type': 'grid_overview',
                'data': overview
            }))
            
            # Listen for messages from admin
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.debug(f"Received from admin {client_id}: {data}")
                    
                    # Handle admin requests
                    # (e.g., subscribe to specific nodes, control commands, etc.)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from admin {client_id}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Admin dashboard disconnected: {client_id}")
        
        except Exception as e:
            logger.error(f"Error handling admin connection {client_id}: {e}", exc_info=True)
        
        finally:
            self.clients.discard(websocket)
    
    async def broadcast_grid_updates(self):
        """Broadcast grid overview to all connected admins"""
        logger.info("Starting admin broadcast loop")
        
        while self._running:
            try:
                if self.clients:
                    # Get grid overview
                    overview = self.aggregator.get_grid_overview()
                    
                    message = json.dumps({
                        'type': 'grid_overview',
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': overview
                    })
                    
                    # Broadcast to all admins
                    dead_clients = set()
                    for client in self.clients:
                        try:
                            await client.send(message)
                        except websockets.exceptions.ConnectionClosed:
                            dead_clients.add(client)
                        except Exception as e:
                            logger.error(f"Error sending to admin: {e}")
                            dead_clients.add(client)
                    
                    # Remove dead connections
                    self.clients -= dead_clients
                
                # Broadcast every 2 seconds
                await asyncio.sleep(2.0)
            
            except Exception as e:
                logger.error(f"Error in admin broadcast loop: {e}", exc_info=True)
                await asyncio.sleep(2.0)

    async def broadcast_event(self, event: dict):
        """Broadcast a custom event to all connected admins"""
        if not self.clients:
            return

        message = json.dumps(event)
        dead_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                dead_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending event to admin: {e}")
                dead_clients.add(client)

        self.clients -= dead_clients
    
    async def start(self):
        """Start the WebSocket server"""
        if self._running:
            logger.warning(f"Admin WebSocket server already running")
            return
        
        self._running = True
        
        logger.info(f"Starting admin WebSocket server on 0.0.0.0:{self.port}")
        
        try:
            self._server = await serve(
                self.handle_client,
                "0.0.0.0",
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Start broadcast task
            self._broadcast_task = asyncio.create_task(self.broadcast_grid_updates())
            
            logger.info(f"✅ Admin WebSocket server started on port {self.port}")
        
        except Exception as e:
            logger.error(f"Failed to start admin WebSocket server: {e}", exc_info=True)
            self._running = False
            raise
    
    async def stop(self):
        """Stop the WebSocket server"""
        if not self._running:
            return
        
        logger.info("Stopping admin WebSocket server")
        self._running = False
        
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
            self.clients.clear()
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        logger.info("Admin WebSocket server stopped")
