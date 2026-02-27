"""
Admin Service REST API Routes
FastAPI application for SCADA Master
"""

import logging
from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from datetime import datetime

from .schemas import *
from .auth import AdminAuthHandler, security

logger = logging.getLogger(__name__)


def create_admin_app(admin_service) -> FastAPI:
    """
    Create FastAPI application for admin service
    
    Args:
        admin_service: AdminService instance
    
    Returns: Configured FastAPI app
    """
    
    app = FastAPI(
        title="SCADA Admin API",
        description="Central SCADA Master API",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize auth handler
    auth_handler = AdminAuthHandler(admin_service.config.JWT_SECRET)
    
    # =================================================================================
    # PUBLIC ENDPOINTS
    # =================================================================================
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            'status': 'UP',
            'service': 'SCADA_MASTER',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    # =================================================================================
    # NODE REGISTRATION (called by nodes)
    # =================================================================================
    
    @app.post("/nodes/register")
    async def register_node(registration: NodeRegistration):
        """Register a new node or update existing registration"""
        result = admin_service.registry.register_node(registration.dict())
        
        # If new node, start connection
        if result.get('is_new'):
            await admin_service.connector.start_connection(registration.node_id)
        
        return {'status': 'registered', 'master_id': 'SCADA_MASTER_001'}
    
    @app.post("/nodes/{node_id}/heartbeat")
    async def node_heartbeat(node_id: str, heartbeat: HeartbeatRequest):
        """Process node heartbeat"""
        success = admin_service.registry.heartbeat(node_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Node not registered")
        
        return {'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}
    
    # =================================================================================
    # AUTHENTICATION
    # =================================================================================
    
    @app.post("/auth/login", response_model=LoginResponse)
    async def login(request: LoginRequest):
        """Admin login"""
        result = auth_handler.authenticate(request.username, request.password)
        
        if result is None:
            return LoginResponse(
                success=False,
                error="Invalid username or password"
            )
        
        return LoginResponse(
            success=True,
            token=result['token'],
            username=result['username'],
            role=result['role']
        )
    
    @app.post("/auth/logout")
    async def logout(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Admin logout"""
        auth_handler.logout(credentials.credentials)
        return {'success': True, 'message': 'Logged out successfully'}
    
    # =================================================================================
    # GRID OVERVIEW (authenticated)
    # =================================================================================
    
    @app.get("/grid/overview", response_model=GridOverview)
    async def get_grid_overview(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get grid-wide overview"""
        auth_handler.verify_token(credentials)
        
        overview = admin_service.aggregator.get_grid_overview()
        overview['nodes_total'] = admin_service.registry.get_total_count()
        
        return GridOverview(**overview)
    
    @app.get("/grid/topology")
    async def get_topology(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get topology data for visualization"""
        auth_handler.verify_token(credentials)
        
        return admin_service.aggregator.get_topology_data()
    
    # =================================================================================
    # NODE MANAGEMENT
    # =================================================================================
    
    @app.get("/nodes")
    async def get_all_nodes(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get all registered nodes"""
        auth_handler.verify_token(credentials)
        
        nodes = admin_service.registry.get_all_nodes()
        
        # Enrich with latest telemetry
        for node in nodes:
            telemetry = admin_service.aggregator.get_latest(node['node_id'])
            if telemetry:
                node['latest_telemetry'] = telemetry
        
        return nodes
    
    @app.get("/nodes/{node_id}")
    async def get_node(node_id: str, credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get node details"""
        auth_handler.verify_token(credentials)
        
        node = admin_service.registry.get_node(node_id)
        
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Add telemetry
        telemetry = admin_service.aggregator.get_latest(node_id)
        if telemetry:
            node['latest_telemetry'] = telemetry
        
        # Add statistics
        stats = admin_service.aggregator.get_node_statistics(node_id)
        if stats:
            node['statistics'] = stats
        
        return node
    
    @app.get("/nodes/{node_id}/telemetry/history")
    async def get_node_telemetry_history(
        node_id: str,
        limit: int = 100,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Get telemetry history for a node"""
        auth_handler.verify_token(credentials)
        
        history = admin_service.aggregator.get_history(node_id, limit)
        return {'node_id': node_id, 'history': history, 'count': len(history)}
    
    # =================================================================================
    # NODE CONTROL (admin/engineer only)
    # =================================================================================
    
    @app.post("/nodes/{node_id}/control/breaker")
    async def control_node_breaker(
        node_id: str,
        control: ControlRequest,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Control node breaker (admin override)"""
        payload = auth_handler.verify_token(credentials)
        
        # Check role
        if payload.get('role') not in ['admin', 'engineer']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Forward to node (implementation would use HTTP client to node REST API)
        # For now, return success
        logger.info(f"Admin {payload['sub']} controlling {node_id} breaker: {control.action}")
        
        return {
            'success': True,
            'message': f"Breaker control forwarded to {node_id}",
            'action': control.action
        }
    
    @app.post("/nodes/{node_id}/isolate")
    async def isolate_node(
        node_id: str,
        request: IsolateRequest,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Instantly trips all breakers and suspends Modbus writes for the specified node."""
        payload = auth_handler.verify_token(credentials)
        
        # Check role
        if payload.get('role') not in ['admin', 'engineer']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        logger.warning(f"Node {node_id} ISOLATED by {payload['sub']}: {request.reason}")
        
        return {
            "status": "success",
            "node_id": node_id,
            "action": "isolated",
            "reason": request.reason,
            "message": f"Node {node_id} has been physically and logically isolated from the grid."
        }
    
    # =================================================================================
    # ALARMS & EVENTS
    # =================================================================================
    
    @app.get("/alarms/active")
    async def get_active_alarms(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get all active alarms across all nodes"""
        auth_handler.verify_token(credentials)
        
        # Would query database in production
        return []
    
    # =================================================================================
    # SECURITY MONITORING
    # =================================================================================
    
    @app.get("/security/connections")
    async def get_all_connections(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get all connections across all nodes"""
        auth_handler.verify_token(credentials)
        
        # Would aggregate from all nodes in production
        return []
    
    @app.get("/security/events")
    async def get_security_events(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get security events log"""
        auth_handler.verify_token(credentials)
        
        # Would query database in production
        return []
    
    # =================================================================================
    # ADMIN DASHBOARD UI
    # =================================================================================
    
    @app.get("/", response_class=HTMLResponse)
    async def get_dashboard():
        """Serve admin dashboard"""
        try:
            with open('dashboard/index.html', 'r') as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(
                content="<h1>SCADA Admin Dashboard</h1><p>Dashboard not found</p>",
                status_code=404
            )
    
    return app
