"""
Modbus TCP Server
S7-200 style - NO AUTHENTICATION (intentionally insecure for research)
Logs all connections and transactions for security monitoring
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext
)
from pymodbus.server import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore.store import BaseModbusDataBlock

from .register_map import RegisterMap

logger = logging.getLogger(__name__)


class MonitoredDataBlock(ModbusSequentialDataBlock):
    """
    Custom data block that logs all read/write operations
    for security monitoring
    """
    
    def __init__(self, address, values, node_id: str, log_callback: Callable):
        super().__init__(address, values)
        self.node_id = node_id
        self.log_callback = log_callback
    
    def setValues(self, address, values):
        """Override to log write operations"""
        # Get client info from current context (if available)
        # Note: This is called from the Modbus server thread
        
        for i, value in enumerate(values):
            reg_addr = address + i
            self.log_callback(
                node_id=self.node_id,
                function_code=6,  # Write Single Register
                register_address=reg_addr,
                value=value,
                direction='WRITE',
                is_write=True
            )
            logger.warning(
                f"Modbus WRITE to {self.node_id}: "
                f"Register {reg_addr} = {value}"
            )
        
        super().setValues(address, values)
    
    def getValues(self, address, count=1):
        """Override to log read operations"""
        values = super().getValues(address, count)
        
        # Log read operation
        self.log_callback(
            node_id=self.node_id,
            function_code=3,  # Read Holding Registers
            register_address=address,
            value=values[0] if values else 0,
            direction='READ',
            is_write=False
        )
        
        return values


class MonitoredCoilBlock(ModbusSequentialDataBlock):
    """Custom coil block that logs all read/write operations"""
    
    def __init__(self, address, values, node_id: str, log_callback: Callable):
        super().__init__(address, values)
        self.node_id = node_id
        self.log_callback = log_callback
    
    def setValues(self, address, values):
        """Override to log coil write operations"""
        for i, value in enumerate(values):
            coil_addr = address + i
            self.log_callback(
                node_id=self.node_id,
                function_code=5,  # Write Single Coil
                register_address=coil_addr,
                value=int(value),
                direction='WRITE',
                is_write=True
            )
            logger.warning(
                f"Modbus WRITE to {self.node_id}: "
                f"Coil {coil_addr} = {value}"
            )
        
        super().setValues(address, values)
    
    def getValues(self, address, count=1):
        """Override to log coil read operations"""
        values = super().getValues(address, count)
        
        self.log_callback(
            node_id=self.node_id,
            function_code=1,  # Read Coils
            register_address=address,
            value=int(values[0]) if values else 0,
            direction='READ',
            is_write=False
        )
        
        return values


class ModbusServer:
    """
    Modbus TCP Server for SCADA node
    
    SECURITY CHARACTERISTICS (S7-200 style):
    - NO authentication required
    - NO encryption
    - ALL connections accepted
    - Writes allowed from ANY IP address
    - All transactions logged for security monitoring
    
    This intentionally mimics legacy SCADA systems for security research.
    """
    
    def __init__(
        self,
        node_id: str,
        unit_id: int,
        port: int,
        update_callback: Callable,
        log_callback: Callable
    ):
        """
        Initialize Modbus server
        
        Args:
            node_id: Node identifier (e.g., "GEN-001")
            unit_id: Modbus unit ID (1-7)
            port: TCP port to listen on
            update_callback: Async function to get current node state
            log_callback: Function to log transactions
        """
        self.node_id = node_id
        self.unit_id = unit_id
        self.port = port
        self.update_callback = update_callback
        self.log_callback = log_callback
        
        # Initialize data blocks
        # Holding registers (0-9): 10 registers
        self.holding_registers = MonitoredDataBlock(
            0,  # Starting address
            [0] * 10,  # 10 registers
            node_id,
            log_callback
        )
        
        # Coils (0-4): 5 coils
        self.coils = MonitoredCoilBlock(
            0,  # Starting address
            [False] * 5,  # 5 coils
            node_id,
            log_callback
        )
        
        # Input registers (read-only copy of holding registers)
        self.input_registers = ModbusSequentialDataBlock(0, [0] * 10)
        
        # Discrete inputs (read-only copy of coils)
        self.discrete_inputs = ModbusSequentialDataBlock(0, [False] * 5)
        
        # Create slave context
        self.slave_context = ModbusSlaveContext(
            di=self.discrete_inputs,  # Discrete Inputs
            co=self.coils,            # Coils
            hr=self.holding_registers, # Holding Registers
            ir=self.input_registers   # Input Registers
        )
        
        # Create server context with single slave
        self.server_context = ModbusServerContext(
            slaves={unit_id: self.slave_context},
            single=False
        )
        
        # Device identification
        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = 'SCADA Simulation Platform'
        self.identity.ProductCode = 'SSP'
        self.identity.VendorUrl = 'https://github.com/scada-sim'
        self.identity.ProductName = f'SCADA Node {node_id}'
        self.identity.ModelName = 'Virtual S7-200'
        self.identity.MajorMinorRevision = '1.0.0'
        
        self._server_task: Optional[asyncio.Task] = None
        self._update_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"Modbus server initialized: {node_id} on port {port}, "
            f"unit ID {unit_id}"
        )
    
    async def update_registers_loop(self):
        """Continuously update registers from simulation state"""
        logger.info(f"Starting register update loop for {self.node_id}")
        
        while self._running:
            try:
                # Get current state from simulation
                state = await self.update_callback()
                
                if state:
                    # Convert state to register values
                    holding_values = RegisterMap.state_to_registers(state)
                    coil_values = RegisterMap.state_to_coils(state)
                    
                    # Update holding registers
                    for addr, value in holding_values.items():
                        # Directly update without triggering logging
                            # Note: addr is 0-indexed from RegisterMap
                            if addr < len(self.holding_registers.values):
                                self.holding_registers.values[addr] = value
                                self.input_registers.values[addr] = value
                    
                    # Update coils
                    for addr, value in coil_values.items():
                            if addr < len(self.coils.values):
                                self.coils.values[addr] = value
                                self.discrete_inputs.values[addr] = value
                
                # Update every second
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(
                    f"Error updating registers for {self.node_id}: {e}",
                    exc_info=True
                )
                await asyncio.sleep(1.0)
    
    async def start(self):
        """Start the Modbus TCP server"""
        if self._running:
            logger.warning(f"Modbus server already running on port {self.port}")
            return
        
        self._running = True
        
        # Start register update loop
        self._update_task = asyncio.create_task(self.update_registers_loop())
        
        # Start Modbus TCP server
        logger.info(
            f"Starting Modbus TCP server for {self.node_id} on 0.0.0.0:{self.port}"
        )
        logger.warning(
            f"⚠️  SECURITY WARNING: Modbus server has NO AUTHENTICATION - "
            f"S7-200 legacy mode"
        )
        
        try:
            # Start the server in background
            self._server_task = asyncio.create_task(
                StartAsyncTcpServer(
                    context=self.server_context,
                    identity=self.identity,
                    address=("0.0.0.0", self.port),
                )
            )
            
            logger.info(
                f"✅ Modbus TCP server started: {self.node_id} on port {self.port}"
            )
            
        except Exception as e:
            logger.error(f"Failed to start Modbus server: {e}", exc_info=True)
            self._running = False
            raise
    
    async def stop(self):
        """Stop the Modbus TCP server"""
        if not self._running:
            return
        
        logger.info(f"Stopping Modbus server for {self.node_id}")
        self._running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Modbus server stopped for {self.node_id}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get Modbus server information"""
        return {
            'node_id': self.node_id,
            'unit_id': self.unit_id,
            'port': self.port,
            'protocol': 'Modbus TCP',
            'authentication': False,
            'encryption': False,
            'registers': RegisterMap.get_all_register_info(),
            'coils': RegisterMap.get_all_coil_info(),
            'status': 'RUNNING' if self._running else 'STOPPED'
        }
