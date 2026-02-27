"""
Modbus Register Map
Defines mapping between simulation tags and Modbus registers
S7-200 style: Simple, no authentication, direct register access
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RegisterDefinition:
    """Definition of a single Modbus register"""
    address: int
    name: str
    unit: str
    scale_factor: float  # Multiply real value by this to get register value
    writable: bool = False
    description: str = ""


class RegisterMap:
    """
    Modbus register map for SCADA nodes
    
    Holding Registers (FC03/FC06):
        Address 0  : bus_voltage_kv      (scaled x100, uint16)
        Address 1  : line_current_a      (scaled x10,  uint16)
        Address 2  : active_power_mw     (scaled x10,  uint16)
        Address 3  : reactive_power_mvar (scaled x10,  uint16)
        Address 4  : frequency_hz        (scaled x100, uint16)
        Address 5  : transformer_temp_c  (scaled x10,  uint16)
        Address 6  : tap_changer_position(raw,         uint16, writable)
        Address 7  : power_factor        (scaled x1000,uint16)
        Address 8  : load_percentage     (scaled x100, uint16)
        Address 9  : generator_rpm       (raw,         uint16)
    
    Coils (FC01/FC05):
        Coil 0 : breaker_state   (writable)
        Coil 1 : relay_trip
        Coil 2 : earth_fault
        Coil 3 : outage_flag
        Coil 4 : feeder_switch   (writable)
    """
    
    # Holding register definitions
    HOLDING_REGISTERS = [
        RegisterDefinition(0, "bus_voltage_kv", "kV", 100.0, False, "Bus voltage"),
        RegisterDefinition(1, "line_current_a", "A", 10.0, False, "Line current"),
        RegisterDefinition(2, "active_power_mw", "MW", 10.0, False, "Active power"),
        RegisterDefinition(3, "reactive_power_mvar", "MVAR", 10.0, False, "Reactive power"),
        RegisterDefinition(4, "frequency_hz", "Hz", 100.0, False, "System frequency"),
        RegisterDefinition(5, "transformer_temp_c", "°C", 10.0, False, "Transformer temperature"),
        RegisterDefinition(6, "tap_position", "-", 1.0, True, "Tap changer position (1-17)"),
        RegisterDefinition(7, "power_factor", "-", 1000.0, False, "Power factor"),
        RegisterDefinition(8, "load_percentage", "%", 100.0, False, "Load percentage"),
        RegisterDefinition(9, "generator_rpm", "RPM", 1.0, False, "Generator speed"),
    ]
    
    # Coil definitions
    COILS = [
        ("breaker_state", 0, True, "Main breaker state (1=closed, 0=open)"),
        ("relay_trip", 1, False, "Protection relay trip status"),
        ("earth_fault", 2, False, "Earth fault indicator"),
        ("outage_flag", 3, False, "Outage flag"),
        ("feeder_switch", 4, True, "Feeder switch state"),
    ]
    
    @classmethod
    def state_to_registers(cls, state: Dict[str, Any]) -> Dict[int, int]:
        """
        Convert node state to Modbus holding register values
        
        Args:
            state: Node state dictionary
        
        Returns: Dict mapping register address to uint16 value
        """
        registers = {}
        
        for reg_def in cls.HOLDING_REGISTERS:
            if reg_def.name in state and state[reg_def.name] is not None:
                raw_value = state[reg_def.name]
                # Scale and convert to uint16
                scaled_value = int(raw_value * reg_def.scale_factor)
                # Clamp to uint16 range
                registers[reg_def.address] = max(0, min(65535, scaled_value))
            else:
                # Default to 0 if tag not present
                registers[reg_def.address] = 0
        
        return registers
    
    @classmethod
    def state_to_coils(cls, state: Dict[str, Any]) -> Dict[int, bool]:
        """
        Convert node state to Modbus coil values
        
        Args:
            state: Node state dictionary
        
        Returns: Dict mapping coil address to boolean value
        """
        coils = {}
        
        for name, address, writable, description in cls.COILS:
            if name in state and state[name] is not None:
                coils[address] = bool(state[name])
            else:
                coils[address] = False
        
        return coils
    
    @classmethod
    def register_to_state_value(cls, address: int, register_value: int) -> Optional[Dict[str, Any]]:
        """
        Convert Modbus register value back to state value
        
        Args:
            address: Register address
            register_value: Uint16 register value
        
        Returns: Dict with tag name and real value, or None if invalid
        """
        for reg_def in cls.HOLDING_REGISTERS:
            if reg_def.address == address:
                real_value = register_value / reg_def.scale_factor
                return {
                    'tag': reg_def.name,
                    'value': real_value,
                    'unit': reg_def.unit
                }
        
        return None
    
    @classmethod
    def is_register_writable(cls, address: int) -> bool:
        """Check if a holding register is writable"""
        for reg_def in cls.HOLDING_REGISTERS:
            if reg_def.address == address:
                return reg_def.writable
        return False
    
    @classmethod
    def is_coil_writable(cls, address: int) -> bool:
        """Check if a coil is writable"""
        for name, addr, writable, description in cls.COILS:
            if addr == address:
                return writable
        return False
    
    @classmethod
    def get_register_info(cls, address: int) -> Optional[Dict[str, Any]]:
        """Get information about a register"""
        for reg_def in cls.HOLDING_REGISTERS:
            if reg_def.address == address:
                return {
                    'address': reg_def.address,
                    'name': reg_def.name,
                    'unit': reg_def.unit,
                    'scale_factor': reg_def.scale_factor,
                    'writable': reg_def.writable,
                    'description': reg_def.description
                }
        return None
    
    @classmethod
    def get_coil_info(cls, address: int) -> Optional[Dict[str, Any]]:
        """Get information about a coil"""
        for name, addr, writable, description in cls.COILS:
            if addr == address:
                return {
                    'address': addr,
                    'name': name,
                    'writable': writable,
                    'description': description
                }
        return None
    
    @classmethod
    def get_all_register_info(cls) -> list:
        """Get information about all registers"""
        return [
            {
                'address': r.address,
                'name': r.name,
                'unit': r.unit,
                'scale_factor': r.scale_factor,
                'writable': r.writable,
                'description': r.description
            }
            for r in cls.HOLDING_REGISTERS
        ]
    
    @classmethod
    def get_all_coil_info(cls) -> list:
        """Get information about all coils"""
        return [
            {
                'address': addr,
                'name': name,
                'writable': writable,
                'description': description
            }
            for name, addr, writable, description in cls.COILS
        ]
