"""
Node Service REST API Routes
FastAPI application with all node endpoints
"""

import logging
import time
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .schemas import *
from .auth import AuthHandler, security

logger = logging.getLogger(__name__)


def create_app(node_service) -> FastAPI:
    """
    Create FastAPI application for node service
    
    Args:
        node_service: Node service instance with simulation, modbus, etc.
    
    Returns: Configured FastAPI app
    """
    
    app = FastAPI(
        title=f"SCADA Node {node_service.config.NODE_ID}",
        description=f"REST API for {node_service.config.NODE_TYPE} node",
        version="1.0.0"
    )
    
    # CORS middleware (allow all origins for development)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize auth handler
    auth_handler = AuthHandler(node_service.config.NODE_ID)
    
    # Track connections for security monitoring
    active_connections = {}
    
    def get_client_ip(request: Request) -> str:
        """Safely extract client IP from request"""
        return request.client.host if request.client else "unknown"
    
    @app.middleware("http")
    async def track_connections(request: Request, call_next):
        """Middleware to track all connections"""
        client_ip = get_client_ip(request)
        client_port = request.client.port if request.client else 0
        
        # Track connection
        conn_key = f"{client_ip}:{client_port}"
        if conn_key not in active_connections:
            active_connections[conn_key] = {
                'protocol': 'HTTP',
                'client_ip': client_ip,
                'client_port': client_port,
                'connected_at': datetime.utcnow().isoformat(),
                'request_count': 0,
                'is_authenticated': False,
                'username': None
            }
        
        active_connections[conn_key]['request_count'] += 1
        
        # Check if authenticated
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = auth_handler.decode_token(token)
                if payload:
                    active_connections[conn_key]['is_authenticated'] = True
                    active_connections[conn_key]['username'] = payload.get('sub')
            except:
                pass
        
        response = await call_next(request)
        return response
    
    # =========================================================================
    # PUBLIC ENDPOINTS (no authentication required)
    # =========================================================================
    
    @app.get("/", response_model=NodeInfo)
    async def get_node_info():
        """Get basic node information"""
        return NodeInfo(
            node_id=node_service.config.NODE_ID,
            node_type=node_service.config.NODE_TYPE,
            version="1.0.0",
            status=node_service.simulation.state.node_state,
            uptime_seconds=time.time() - node_service.start_time
        )
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint"""
        services = {
            'simulation': 'RUNNING' if node_service.simulation._running else 'STOPPED',
            'modbus': 'RUNNING' if node_service.modbus_server._running else 'STOPPED',
            'api': 'RUNNING'
        }
        
        return HealthResponse(
            status='UP',
            node_id=node_service.config.NODE_ID,
            timestamp=datetime.utcnow().isoformat(),
            services=services
        )
    
    @app.get("/telemetry", response_model=TelemetryData)
    async def get_telemetry():
        """Get current telemetry data"""
        state = node_service.simulation.get_state()
        return TelemetryData(**state.to_dict())
    
    @app.get("/status")
    async def get_status():
        """Get operational status summary"""
        state = node_service.simulation.get_state()
        alarms = node_service.simulation.get_alarms()
        
        return {
            'node_id': node_service.config.NODE_ID,
            'timestamp': datetime.utcnow().isoformat(),
            'operational_state': state.node_state,
            'breaker_state': state.breaker_state,
            'frequency_hz': state.frequency_hz,
            'active_power_mw': state.active_power_mw,
            'active_alarms': len(alarms),
            'critical_alarms': len([a for a in alarms if a['priority'] == 1])
        }
    
    @app.get("/modbus/info", response_model=ModbusInfo)
    async def get_modbus_info():
        """Get Modbus server configuration and register map"""
        info = node_service.modbus_server.get_info()
        return ModbusInfo(**info)
    
    @app.get("/connections", response_model=ConnectionListResponse)
    async def get_connections():
        """Get all active connections to this node"""
        connections = [
            Connection(**conn)
            for conn in active_connections.values()
        ]
        return ConnectionListResponse(
            connections=connections,
            total=len(connections)
        )
    
    # =========================================================================
    # UI ENDPOINT
    # =========================================================================
    
    @app.get("/ui", response_class=HTMLResponse)
    async def get_dashboard():
        """Serve operator dashboard"""
        try:
            with open('dashboard/index.html', 'r') as f:
                html = f.read()
                # Replace placeholders
                html = html.replace('{{NODE_ID}}', node_service.config.NODE_ID)
                html = html.replace('{{NODE_TYPE}}', node_service.config.NODE_TYPE)
                return HTMLResponse(content=html)
        except FileNotFoundError:
            return HTMLResponse(
                content=f"<h1>Node {node_service.config.NODE_ID}</h1><p>Dashboard not found</p>",
                status_code=404
            )
    
    # =========================================================================
    # AUTHENTICATION ENDPOINTS
    # =========================================================================
    
    @app.post("/auth/login", response_model=LoginResponse)
    async def login(request: LoginRequest, req: Request):
        """Operator login"""
        token = auth_handler.authenticate(request.username, request.password)
        
        if token is None:
            # Log failed login attempt
            logger.warning(
                f"Failed login attempt: {request.username} from {get_client_ip(req)}"
            )
            return LoginResponse(
                success=False,
                error="Invalid username or password"
            )
        
        # Log successful login
        logger.info(
            f"Successful login: {request.username} from {get_client_ip(req)}"
        )
        
        # Log to audit
        await node_service.log_operator_action(
            operator=request.username,
            operator_ip=get_client_ip(req),
            action_type='LOGIN',
            action_detail={'method': 'password'},
            result='SUCCESS'
        )
        
        return LoginResponse(
            success=True,
            token=token,
            operator=request.username,
            node_id=node_service.config.NODE_ID
        )
    
    @app.post("/auth/logout")
    async def logout(
        credentials: HTTPAuthorizationCredentials = Security(security),
        req: Request = None
    ):
        """Operator logout"""
        username = auth_handler.verify_token(credentials)
        auth_handler.logout(credentials.credentials)
        
        # Log logout
        await node_service.log_operator_action(
            operator=username,
            operator_ip=get_client_ip(req) if req else 'unknown',
            action_type='LOGOUT',
            action_detail={},
            result='SUCCESS'
        )
        
        return {'success': True, 'message': 'Logged out successfully'}
    
    # =========================================================================
    # AUTHENTICATED ENDPOINTS (operator login required)
    # =========================================================================
    
    @app.get("/control/panel")
    async def get_control_panel(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Get controllable parameters"""
        username = auth_handler.verify_token(credentials)
        
        state = node_service.simulation.get_state()
        
        controls = {
            'breaker': {
                'available': True,
                'current_state': state.breaker_state,
                'actions': ['open', 'close']
            }
        }
        
        # Add tap changer control for substations
        if state.tap_position is not None:
            controls['tap_changer'] = {
                'available': True,
                'current_position': state.tap_position,
                'min_position': 1,
                'max_position': 17
            }
        
        # Add generator setpoint control for generation nodes
        if state.generator_rpm is not None:
            controls['power_setpoint'] = {
                'available': True,
                'current_mw': state.active_power_mw,
                'min_mw': 100.0,
                'max_mw': 800.0
            }
        
        return controls
    
    @app.post("/control/breaker", response_model=BreakerControlResponse)
    async def control_breaker(
        request: BreakerControlRequest,
        req: Request,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Open or close breaker"""
        username = auth_handler.verify_token(credentials)
        
        # Execute control action
        new_state = request.action == 'close'
        result = node_service.simulation.set_breaker(new_state, request.reason)
        
        # Log action
        await node_service.log_operator_action(
            operator=username,
            operator_ip=get_client_ip(req),
            action_type='BREAKER_CONTROL',
            action_detail={
                'action': request.action,
                'reason': request.reason,
                'old_state': result.get('old_state'),
                'new_state': result.get('new_state')
            },
            result='SUCCESS' if result.get('success') else 'FAILED'
        )
        
        if result.get('success'):
            return BreakerControlResponse(**result, reason=request.reason)
        else:
            return BreakerControlResponse(
                success=False,
                action=request.action,
                reason=request.reason,
                error=result.get('error', 'Unknown error')
            )
    
    @app.post("/control/tap", response_model=TapControlResponse)
    async def control_tap(
        request: TapControlRequest,
        req: Request,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Set tap changer position"""
        username = auth_handler.verify_token(credentials)
        
        # Execute control action
        result = node_service.simulation.set_tap_position(
            request.position,
            request.reason
        )
        
        # Log action
        await node_service.log_operator_action(
            operator=username,
            operator_ip=get_client_ip(req),
            action_type='TAP_CONTROL',
            action_detail={
                'position': request.position,
                'reason': request.reason,
                'old_position': result.get('old_position'),
                'new_position': result.get('new_position')
            },
            result='SUCCESS' if result.get('success') else 'FAILED'
        )
        
        if result.get('success'):
            return TapControlResponse(**result, reason=request.reason)
        else:
            return TapControlResponse(
                success=False,
                reason=request.reason,
                error=result.get('error', 'Unknown error')
            )
    
    @app.post("/control/setpoint", response_model=SetpointResponse)
    async def set_power_setpoint(
        request: SetpointRequest,
        req: Request,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Set power generation setpoint (generation nodes only)"""
        username = auth_handler.verify_token(credentials)
        
        # Check if node supports power setpoint
        if not hasattr(node_service.simulation, 'set_power_setpoint'):
            return SetpointResponse(
                success=False,
                tag=request.tag,
                reason=request.reason,
                error="Node does not support power setpoint control"
            )
        
        # Execute control action
        result = node_service.simulation.set_power_setpoint(
            request.value,
            reason=request.reason
        )
        
        # Log action
        await node_service.log_operator_action(
            operator=username,
            operator_ip=get_client_ip(req),
            action_type='SETPOINT_CONTROL',
            action_detail={
                'tag': request.tag,
                'value': request.value,
                'reason': request.reason
            },
            result='SUCCESS' if result.get('success') else 'FAILED'
        )
        
        if result.get('success'):
            return SetpointResponse(
                success=True,
                action='setpoint_changed',
                old_value=result.get('old_setpoint_mw'),
                new_value=request.value,
                tag=request.tag,
                reason=request.reason
            )
        else:
            return SetpointResponse(
                success=False,
                tag=request.tag,
                reason=request.reason,
                error=result.get('error', 'Unknown error')
            )
    
    @app.post("/voltage")
    async def adjust_voltage(
        request: VoltageAdjustRequest,
        req: Request,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Adjust node voltage with threshold checking"""
        username = auth_handler.verify_token(credentials)
        
        # Get voltage thresholds for this node
        if 'GEN' in node_service.config.NODE_ID:
            thresholds = {'min': 370, 'safe_max': 390, 'max': 395}
        elif 'SUB' in node_service.config.NODE_ID:
            thresholds = {'min': 120, 'safe_max': 135, 'max': 150}
        else:
            thresholds = {'min': 8, 'safe_max': 12, 'max': 14}
        
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
            
            # Verify password against stored credentials
            user_creds = auth_handler.users.get(username, {})
            if request.password != user_creds.get('password'):
                logger.warning(f"Invalid password attempt for voltage adjustment by {username}")
                raise HTTPException(status_code=401, detail="Invalid password")
        
        # Check hard maximum
        if request.voltage_kv > thresholds['max']:
            raise HTTPException(status_code=400, detail=f"Voltage {request.voltage_kv} exceeds hard maximum {thresholds['max']}")
        
        # APPLY VOLTAGE TO SIMULATION
        node_service.simulation.set_applied_voltage(request.voltage_kv)
        logger.info(f"Voltage adjusted to {request.voltage_kv} kV by {username}")
        
        # Log action
        await node_service.log_operator_action(
            operator=username,
            operator_ip=get_client_ip(req),
            action_type='VOLTAGE_ADJUSTMENT',
            action_detail={
                'requested_voltage_kv': request.voltage_kv,
                'reason': request.reason,
                'password_required': request.voltage_kv > thresholds['safe_max']
            },
            result='SUCCESS'
        )
        
        return {
            "status": "success",
            "node_id": node_service.config.NODE_ID,
            "voltage_kv": request.voltage_kv,
            "threshold": thresholds['safe_max'],
            "message": f"Voltage adjusted to {request.voltage_kv} kV"
        }
    
    @app.post("/standby")
    async def standby_node(
        request: StandbyRequest,
        req: Request,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Put node on standby"""
        username = auth_handler.verify_token(credentials)
        
        # APPLY STANDBY TO SIMULATION
        node_service.simulation.set_standby(True)
        logger.info(f"Node put on standby for {request.duration_minutes} min by {username}")
        
        # Log action
        await node_service.log_operator_action(
            operator=username,
            operator_ip=get_client_ip(req),
            action_type='STANDBY',
            action_detail={
                'duration_minutes': request.duration_minutes,
                'reason': request.reason
            },
            result='SUCCESS'
        )
        
        return {
            "status": "success",
            "node_id": node_service.config.NODE_ID,
            "state": "STANDBY",
            "duration_minutes": request.duration_minutes,
            "message": f"Node is now on standby"
        }
    
    @app.post("/isolate")
    async def isolate_node(
        request: IsolateRequest,
        req: Request,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Isolate node from grid"""
        username = auth_handler.verify_token(credentials)
        
        # APPLY ISOLATION TO SIMULATION
        node_service.simulation.set_isolation(True)
        logger.warning(f"Node ISOLATED by {username}: {request.reason}")
        
        # Log action
        await node_service.log_operator_action(
            operator=username,
            operator_ip=get_client_ip(req),
            action_type='ISOLATION',
            action_detail={
                'reason': request.reason,
                'force': request.force
            },
            result='SUCCESS'
        )
        
        return {
            "status": "success",
            "node_id": node_service.config.NODE_ID,
            "action": "isolated",
            "reason": request.reason,
            "message": f"Node has been physically and logically isolated from the grid."
        }
    
    @app.post("/start")
    async def start_node(
        request: StartNodeRequest,
        req: Request,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Start node from standby"""
        username = auth_handler.verify_token(credentials)
        
        # CLEAR STANDBY FROM SIMULATION
        node_service.simulation.set_standby(False)
        logger.info(f"Node started from standby by {username}: {request.reason}")
        
        # Log action
        await node_service.log_operator_action(
            operator=username,
            operator_ip=get_client_ip(req),
            action_type='START',
            action_detail={
                'reason': request.reason
            },
            result='SUCCESS'
        )
        
        return {
            "status": "success",
            "node_id": node_service.config.NODE_ID,
            "state": "ONLINE",
            "message": "Node is now online"
        }
    
    @app.get("/state")
    async def get_node_state(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Get current operational state of node"""
        username = auth_handler.verify_token(credentials)
        
        state = node_service.simulation.get_state()
        
        return {
            "node_id": node_service.config.NODE_ID,
            "state": node_service.simulation.get_operational_state(),
            "operational_state": state.node_state,
            "is_isolated": node_service.simulation.is_isolated(),
            "is_standby": node_service.simulation.is_standby(),
            "current_voltage_kv": state.bus_voltage_kv,
            "applied_voltage_kv": node_service.simulation.get_applied_voltage(),
            "breaker_state": state.breaker_state,
            "active_power_mw": state.active_power_mw
        }
    
    @app.get("/voltage/threshold")
    async def get_voltage_threshold(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Get voltage thresholds for this node"""
        username = auth_handler.verify_token(credentials)
        
        # Thresholds vary by node type
        if 'GEN' in node_service.config.NODE_ID:
            thresholds = {
                'min': 370,
                'safe_max': 390,
                'max': 410
            }
        elif 'SUB' in node_service.config.NODE_ID:
            thresholds = {
                'min': 120,
                'safe_max': 135,
                'max': 150
            }
        else:
            thresholds = {
                'min': 8,
                'safe_max': 12,
                'max': 14
            }
        
        return {
            "node_id": node_service.config.NODE_ID,
            "min_voltage_kv": thresholds['min'],
            "safe_max_voltage_kv": thresholds['safe_max'],
            "hard_max_voltage_kv": thresholds['max'],
            "requires_password_above": thresholds['safe_max']
        }
    
    @app.get("/alarms", response_model=AlarmListResponse)
    async def get_alarms(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Get active alarms"""
        username = auth_handler.verify_token(credentials)
        
        alarms = node_service.simulation.get_alarms()
        alarm_objects = [Alarm(**a) for a in alarms]
        
        return AlarmListResponse(
            alarms=alarm_objects,
            total=len(alarm_objects)
        )
    
    @app.get("/events", response_model=EventListResponse)
    async def get_events(
        limit: int = 100,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Get recent events"""
        username = auth_handler.verify_token(credentials)
        
        # Get events from node service
        events = await node_service.get_recent_events(limit)
        
        return EventListResponse(
            events=events,
            total=len(events)
        )
    
    @app.get("/audit", response_model=AuditListResponse)
    async def get_audit_log(
        limit: int = 100,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        """Get operator action audit log"""
        username = auth_handler.verify_token(credentials)
        
        # Get audit entries from node service
        entries = await node_service.get_audit_log(limit)
        
        return AuditListResponse(
            entries=entries,
            total=len(entries)
        )
    
    return app
