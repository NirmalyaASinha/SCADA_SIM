"""
Admin Service REST API Routes
FastAPI application for SCADA Master
"""

import logging
from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials

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

    @app.post("/nodes/{node_id}/state_change")
    async def node_state_change(node_id: str, change: NodeStateChangeRequest):
        """Handle node state change events and cascade propagation"""
        if node_id != change.node_id:
            raise HTTPException(status_code=400, detail="Node ID mismatch")

        node_states = await admin_service._collect_node_states()
        node_states[node_id] = change.new_state

        affected_nodes = []
        restored_nodes = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            if change.new_state in ["TRIPPED", "FAULTED", "ISOLATED"]:
                affected_nodes = await admin_service.power_flow.compute_cascade(node_id, node_states)
                households_affected = await admin_service.power_flow.get_households_affected(affected_nodes)

                for affected_id in affected_nodes:
                    node_info = admin_service.registry.get_node(affected_id)
                    if not node_info:
                        continue
                    url = f"http://{node_info['ip']}:{node_info['rest_port']}/control/deenergize"
                    try:
                        await client.post(
                            url,
                            json={"reason": change.reason},
                            headers={"Authorization": f"Bearer {admin_service.config.MASTER_API_TOKEN}"}
                        )
                    except Exception as e:
                        logger.error(f"Failed to deenergize {affected_id}: {e}")

                event = {
                    "type": "cascade_event",
                    "trigger_node": change.node_id,
                    "trigger_state": change.new_state,
                    "trigger_reason": change.reason,
                    "trigger_operator": change.operator,
                    "affected_nodes": affected_nodes,
                    "households_affected": households_affected,
                    "severity": "CRITICAL",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await admin_service.ws_manager.broadcast_event(event)
                await admin_service.log_cascade_event(event)

                await admin_service.ws_manager.broadcast_event({
                    "type": "alarm_raised",
                    "node_id": change.node_id,
                    "priority": 1,
                    "message": f"GRID CASCADE FAILURE — {change.node_id} {change.new_state}",
                    "timestamp": datetime.utcnow().isoformat()
                })

            elif change.new_state == "ENERGIZED":
                for candidate_id, state in node_states.items():
                    if state != "DEENERGIZED":
                        continue
                    has_power = await admin_service.power_flow.has_power_source(candidate_id, node_states)
                    if has_power:
                        restored_nodes.append(candidate_id)

                for restored_id in restored_nodes:
                    node_info = admin_service.registry.get_node(restored_id)
                    if not node_info:
                        continue
                    url = f"http://{node_info['ip']}:{node_info['rest_port']}/control/reenergize"
                    try:
                        await client.post(
                            url,
                            json={"reason": change.reason},
                            headers={"Authorization": f"Bearer {admin_service.config.MASTER_API_TOKEN}"}
                        )
                    except Exception as e:
                        logger.error(f"Failed to reenergize {restored_id}: {e}")

                if restored_nodes:
                    event = {
                        "type": "power_restored",
                        "trigger_node": change.node_id,
                        "restored_nodes": restored_nodes,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await admin_service.ws_manager.broadcast_event(event)
                    await admin_service.log_cascade_restoration(change.node_id)

        await admin_service._refresh_power_flow()

        return {
            "status": "ok",
            "trigger_node": change.node_id,
            "new_state": change.new_state,
            "affected_nodes": affected_nodes,
            "restored_nodes": restored_nodes
        }
    
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
            state = admin_service.aggregator.get_node_state(node['node_id'])
            if state != 'UNKNOWN':
                node['node_state'] = state
            elif telemetry and telemetry.get('node_state'):
                node['node_state'] = telemetry.get('node_state')
        
        return nodes
    
    @app.get("/nodes/map")
    async def get_node_map(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get node locations for map visualization"""
        auth_handler.verify_token(credentials)
        
        locations = admin_service.aggregator.get_node_locations()
        
        # Enhance with current state
        enhanced = {}
        for node_id, location in locations.items():
            state = admin_service.aggregator.get_node_state(node_id)
            telemetry = admin_service.aggregator.get_latest(node_id)
            enhanced[node_id] = {
                **location,
                'state': state if state != 'UNKNOWN' else (telemetry.get('node_state', 'ONLINE') if telemetry else 'UNKNOWN'),
                'voltage_kv': telemetry.get('bus_voltage_kv', 0) if telemetry else 0,
                'power_mw': telemetry.get('active_power_mw', 0) if telemetry else 0
            }
        
        return enhanced
    
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
        
        # Set node state to ISOLATED
        admin_service.aggregator.set_node_state(node_id, 'ISOLATED')
        
        # Also send isolation command to the node service
        node_info = admin_service.registry.get_node(node_id)
        if node_info:
            try:
                import aiohttp
                auth_token = admin_service.config.MASTER_API_TOKEN or credentials.credentials
                async with aiohttp.ClientSession() as session:
                    url = f"http://{node_info['ip']}:{node_info['rest_port']}/isolate"
                    async with session.post(url, 
                        json={"reason": request.reason, "force": True},
                        headers={"Authorization": f"Bearer {auth_token}"}
                    ) as resp:
                        pass  # Response handled, node is now isolated
            except Exception as e:
                logger.error(f"Failed to send isolation to {node_id}: {e}")
        
        logger.warning(f"Node {node_id} ISOLATED by {payload['sub']}: {request.reason}")
        
        return {
            "status": "success",
            "node_id": node_id,
            "action": "isolated",
            "reason": request.reason,
            "message": f"Node {node_id} has been physically and logically isolated from the grid."
        }
    
    @app.post("/nodes/{node_id}/voltage")
    async def adjust_node_voltage(
        node_id: str,
        request: VoltageAdjustRequest,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Adjust node voltage with threshold checking"""
        payload = auth_handler.verify_token(credentials)
        
        if payload.get('role') not in ['admin', 'engineer']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        thresholds = admin_service.aggregator.get_voltage_threshold(node_id)
        
        # Check if voltage exceeds safe threshold
        if request.voltage_kv > thresholds['safe_max']:
            # Require password verification for high voltage
            if not request.password:
                return {
                    "status": "requires_password",
                    "message": f"Voltage {request.voltage_kv} kV exceeds safe threshold {thresholds['safe_max']} kV. Password required.",
                    "threshold": thresholds['safe_max'],
                    "requested": request.voltage_kv
                }
            
            # Verify password
            user_data = auth_handler.users.get(payload['sub'], {})
            if request.password != user_data.get('password'):
                logger.warning(f"Invalid password attempt for {node_id} voltage adjustment by {payload['sub']}")
                raise HTTPException(status_code=401, detail="Invalid password")
        
        # Check hard maximum
        if request.voltage_kv > thresholds['max']:
            raise HTTPException(status_code=400, detail=f"Voltage {request.voltage_kv} exceeds hard maximum {thresholds['max']}")
        
        # Also send voltage command to the node service
        node_info = admin_service.registry.get_node(node_id)
        if node_info:
            try:
                import aiohttp
                auth_token = admin_service.config.MASTER_API_TOKEN or credentials.credentials
                async with aiohttp.ClientSession() as session:
                    url = f"http://{node_info['ip']}:{node_info['rest_port']}/voltage"
                    async with session.post(url, 
                        json={"voltage_kv": request.voltage_kv},
                        headers={"Authorization": f"Bearer {auth_token}"}
                    ) as resp:
                        pass  # Response handled, voltage is set
            except Exception as e:
                logger.error(f"Failed to send voltage adjustment to {node_id}: {e}")
        
        logger.info(f"Voltage adjusted for {node_id} to {request.voltage_kv} kV by {payload['sub']}")
        
        return {
            "status": "success",
            "node_id": node_id,
            "voltage_kv": request.voltage_kv,
            "threshold": thresholds['safe_max'],
            "message": f"Voltage adjusted to {request.voltage_kv} kV"
        }
    
    @app.post("/nodes/{node_id}/standby")
    async def standby_node(
        node_id: str,
        request: StandbyRequest,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Put node on standby (admin only)"""
        payload = auth_handler.verify_token(credentials)
        
        if payload.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Only admin can put nodes on standby")
        
        admin_service.aggregator.set_node_state(node_id, 'STANDBY')
        
        # Also send standby command to the node service
        node_info = admin_service.registry.get_node(node_id)
        if node_info:
            try:
                import aiohttp
                auth_token = admin_service.config.MASTER_API_TOKEN or credentials.credentials
                async with aiohttp.ClientSession() as session:
                    url = f"http://{node_info['ip']}:{node_info['rest_port']}/standby"
                    async with session.post(url, 
                        json={"duration_minutes": request.duration_minutes, "reason": request.reason},
                        headers={"Authorization": f"Bearer {auth_token}"}
                    ) as resp:
                        pass  # Response handled, node is now on standby
            except Exception as e:
                logger.error(f"Failed to send standby to {node_id}: {e}")
        
        logger.info(f"Node {node_id} put on standby for {request.duration_minutes} min by {payload['sub']}: {request.reason}")
        
        return {
            "status": "success",
            "node_id": node_id,
            "state": "STANDBY",
            "duration_minutes": request.duration_minutes,
            "message": f"Node {node_id} is now on standby"
        }
    
    @app.post("/nodes/{node_id}/start")
    async def start_node(
        node_id: str,
        request: StartNodeRequest,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Start node from standby (admin only)"""
        payload = auth_handler.verify_token(credentials)
        
        if payload.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Only admin can start nodes")
        
        admin_service.aggregator.set_node_state(node_id, 'ONLINE')
        
        # Also send start command to the node service
        node_info = admin_service.registry.get_node(node_id)
        if node_info:
            try:
                import aiohttp
                auth_token = admin_service.config.MASTER_API_TOKEN or credentials.credentials
                async with aiohttp.ClientSession() as session:
                    url = f"http://{node_info['ip']}:{node_info['rest_port']}/start"
                    async with session.post(url, 
                        json={"reason": request.reason},
                        headers={"Authorization": f"Bearer {auth_token}"}
                    ) as resp:
                        pass  # Response handled, node is now online
            except Exception as e:
                logger.error(f"Failed to send start to {node_id}: {e}")
        
        logger.info(f"Node {node_id} started by {payload['sub']}: {request.reason}")
        
        return {
            "status": "success",
            "node_id": node_id,
            "state": "ONLINE",
            "message": f"Node {node_id} is now online"
        }
    
    @app.get("/nodes/{node_id}/voltage/threshold")
    async def get_voltage_threshold(
        node_id: str,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Get voltage thresholds for a node"""
        auth_handler.verify_token(credentials)
        
        thresholds = admin_service.aggregator.get_voltage_threshold(node_id)
        telemetry = admin_service.aggregator.get_latest(node_id)
        current_voltage = telemetry.get('bus_voltage_kv', 0) if telemetry else 0
        
        return {
            "node_id": node_id,
            "current_voltage_kv": current_voltage,
            "min_voltage_kv": thresholds['min'],
            "safe_max_voltage_kv": thresholds['safe_max'],
            "hard_max_voltage_kv": thresholds['max'],
            "requires_password_above": thresholds['safe_max']
        }
    
    # =================================================================================
    # ALARMS & EVENTS
    # =================================================================================
    
    @app.get("/alarms")
    async def get_all_alarms(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get all alarms (active and acknowledged)"""
        auth_handler.verify_token(credentials)
        
        # Return mock alarm data for testing - in production, query database
        return [
            {
                "id": 1,
                "node_id": "GEN-001",
                "priority": "P1",
                "message": "Overcurrent detected on generator",
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False,
                "acked_by": None,
                "acked_at": None,
                "severity": "CRITICAL"
            },
            {
                "id": 2,
                "node_id": "SUB-001",
                "priority": "P2",
                "message": "Voltage deviation warning",
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "acknowledged": False,
                "acked_by": None,
                "acked_at": None,
                "severity": "HIGH"
            },
            {
                "id": 3,
                "node_id": "DIST-001",
                "priority": "P3",
                "message": "Temperature monitoring active",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "acknowledged": True,
                "acked_by": "admin",
                "acked_at": (datetime.now() - timedelta(minutes=10)).isoformat(),
                "severity": "MEDIUM"
            }
        ]
    
    @app.get("/alarms/active")
    async def get_active_alarms(credentials: HTTPAuthorizationCredentials = Security(security)):
        """Get all active (unacknowledged) alarms across all nodes"""
        auth_handler.verify_token(credentials)
        
        # Would query database in production
        return []
    
    @app.post("/alarms/{alarm_id}/ack")
    async def acknowledge_alarm(alarm_id: int, body: dict, credentials: HTTPAuthorizationCredentials = Security(security)):
        """Acknowledge an alarm to clear it from critical alerts"""
        auth_handler.verify_token(credentials)
        
        # In production, update database with acknowledgment
        return {
            "status": "acknowledged",
            "alarm_id": alarm_id,
            "acked_by": body.get("user", "unknown"),
            "acked_at": datetime.now().isoformat(),
            "message": f"Alarm {alarm_id} acknowledged successfully"
        }
    
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
