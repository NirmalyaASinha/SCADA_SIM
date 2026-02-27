"""
Telemetry Aggregator
Collects and aggregates telemetry from all nodes
Provides grid-wide statistics and KPIs
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class TelemetryAggregator:
    """
    Aggregates telemetry from all SCADA nodes
    Provides grid-wide statistics
    """
    
    def __init__(self):
        # Latest telemetry from each node: node_id -> telemetry_dict
        self.latest_telemetry: Dict[str, Dict] = {}
        
        # Telemetry history (limited, in-memory)
        self.history: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history_length = 1000
        
        # Node state tracking: node_id -> state (ONLINE, STANDBY, ISOLATED)
        self.node_states: Dict[str, str] = {}
        
        # Node locations for mapping
        self.node_locations: Dict[str, Dict] = {
            'GEN-001': {'x': 100, 'y': 50, 'label': 'Generation-1'},
            'GEN-002': {'x': 400, 'y': 50, 'label': 'Generation-2'},
            'SUB-001': {'x': 50, 'y': 200, 'label': 'Transmission-1'},
            'SUB-002': {'x': 250, 'y': 200, 'label': 'Transmission-2'},
            'SUB-003': {'x': 450, 'y': 200, 'label': 'Transmission-3'},
            'DIST-001': {'x': 150, 'y': 350, 'label': 'Distribution-1'},
            'DIST-002': {'x': 350, 'y': 350, 'label': 'Distribution-2'},
        }
        
        # Voltage thresholds: min and max allowed voltage (kV)
        self.voltage_thresholds = {
            'GEN-001': {'min': 370, 'max': 395, 'safe_max': 390},
            'GEN-002': {'min': 370, 'max': 395, 'safe_max': 390},
            'SUB-001': {'min': 120, 'max': 140, 'safe_max': 135},
            'SUB-002': {'min': 120, 'max': 140, 'safe_max': 135},
            'SUB-003': {'min': 120, 'max': 140, 'safe_max': 135},
            'DIST-001': {'min': 8, 'max': 13, 'safe_max': 12},
            'DIST-002': {'min': 8, 'max': 13, 'safe_max': 12},
        }
        
        logger.info("Telemetry aggregator initialized")
    
    def update_telemetry(self, node_id: str, telemetry: Dict):
        """
        Update telemetry for a node
        
        Args:
            node_id: Node identifier
            telemetry: Telemetry data dictionary
        """
        # Store latest telemetry
        self.latest_telemetry[node_id] = {
            **telemetry,
            'node_id': node_id,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Add to history
        self.history[node_id].append({
            **telemetry,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Trim history
        if len(self.history[node_id]) > self.max_history_length:
            self.history[node_id] = self.history[node_id][-self.max_history_length:]
    
    def get_latest(self, node_id: str) -> Optional[Dict]:
        """Get latest telemetry for a node"""
        return self.latest_telemetry.get(node_id)
    
    def get_all_latest(self) -> Dict[str, Dict]:
        """Get latest telemetry for all nodes"""
        return self.latest_telemetry.copy()
    
    def get_history(self, node_id: str, limit: int = 100) -> List[Dict]:
        """Get telemetry history for a node"""
        history = self.history.get(node_id, [])
        return history[-limit:]
    
    def get_grid_overview(self) -> Dict:
        """
        Calculate grid-wide KPIs
        
        Returns: Dictionary of aggregated metrics
        """
        if not self.latest_telemetry:
            return {
                'total_generation_mw': 0.0,
                'total_load_mw': 0.0,
                'grid_frequency_hz': 50.0,
                'grid_losses_mw': 0.0,
                'loss_percentage': 0.0,
                'nodes_online': 0,
                'nodes_total': 0,
                'timestamp': datetime.utcnow().isoformat(),
                'critical_alarms': 0,
                'warning_alarms': 0
            }
        
        # Aggregate power
        total_generation = 0.0
        total_load = 0.0
        frequencies = []
        
        for node_id, data in self.latest_telemetry.items():
            power = data.get('active_power_mw', 0.0)
            node_type = data.get('node_type', '')
            
            if node_type == 'generation':
                total_generation += power
            elif node_type in ['transmission', 'distribution']:
                total_load += power
            
            # Collect frequencies
            if 'frequency_hz' in data:
                frequencies.append(data['frequency_hz'])
        
        # Calculate average frequency
        avg_frequency = sum(frequencies) / len(frequencies) if frequencies else 50.0
        
        # Calculate losses
        grid_losses = total_generation - total_load
        
        return {
            'total_generation_mw': round(total_generation, 1),
            'total_load_mw': round(total_load, 1),
            'grid_frequency_hz': round(avg_frequency, 3),
            'grid_losses_mw': round(grid_losses, 1),
            'loss_percentage': round((grid_losses / total_generation * 100) if total_generation > 0 else 0.0, 2),
            'nodes_online': len(self.latest_telemetry),
            'nodes_total': len(self.latest_telemetry),  # Will be updated by registry
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_topology_data(self) -> Dict:
        """
        Generate topology data for React Flow visualization
        
        Returns: Dict with nodes and edges
        """
        nodes = []
        edges = []
        
        # Define node positions (manual layout for 7 nodes)
        positions = {
            'GEN-001': {'x': 100, 'y': 50},
            'GEN-002': {'x': 400, 'y': 50},
            'SUB-001': {'x': 50, 'y': 200},
            'SUB-002': {'x': 250, 'y': 200},
            'SUB-003': {'x': 450, 'y': 200},
            'DIST-001': {'x': 150, 'y': 350},
            'DIST-002': {'x': 350, 'y': 350},
        }
        
        # Create nodes
        for node_id, telemetry in self.latest_telemetry.items():
            node_type = telemetry.get('node_type', '')
            node_state = telemetry.get('node_state', 'UNKNOWN')
            
            nodes.append({
                'id': node_id,
                'type': node_type,
                'position': positions.get(node_id, {'x': 0, 'y': 0}),
                'data': {
                    'label': node_id,
                    'state': node_state,
                    'power_mw': telemetry.get('active_power_mw', 0.0),
                    'voltage_kv': telemetry.get('bus_voltage_kv', 0.0),
                    'breaker_state': telemetry.get('breaker_state', False)
                }
            })
        
        # Create edges (connections between nodes)
        # GEN-001 -> SUB-001, SUB-002
        edges.extend([
            {'id': 'e1', 'source': 'GEN-001', 'target': 'SUB-001'},
            {'id': 'e2', 'source': 'GEN-001', 'target': 'SUB-002'},
            {'id': 'e3', 'source': 'GEN-002', 'target': 'SUB-002'},
            {'id': 'e4', 'source': 'GEN-002', 'target': 'SUB-003'},
            {'id': 'e5', 'source': 'SUB-001', 'target': 'DIST-001'},
            {'id': 'e6', 'source': 'SUB-002', 'target': 'DIST-001'},
            {'id': 'e7', 'source': 'SUB-002', 'target': 'DIST-002'},
            {'id': 'e8', 'source': 'SUB-003', 'target': 'DIST-002'},
        ])
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def set_node_state(self, node_id: str, state: str):
        """Set node operational state (ONLINE, STANDBY, ISOLATED)"""
        if state not in ['ONLINE', 'STANDBY', 'ISOLATED']:
            raise ValueError(f"Invalid state: {state}")
        self.node_states[node_id] = state
        logger.info(f"Node {node_id} state set to {state}")
    
    def get_node_state(self, node_id: str) -> str:
        """Get node operational state"""
        return self.node_states.get(node_id, 'UNKNOWN')
    
    def get_node_locations(self) -> Dict:
        """Get map of all node locations"""
        return self.node_locations.copy()
    
    def get_voltage_threshold(self, node_id: str) -> Dict:
        """Get voltage thresholds for a node"""
        return self.voltage_thresholds.get(node_id, {'min': 0, 'max': 400, 'safe_max': 380})
    
    def is_voltage_in_safe_range(self, node_id: str, voltage_kv: float) -> bool:
        """Check if voltage is within safe operating range"""
        thresholds = self.get_voltage_threshold(node_id)
        return thresholds['min'] <= voltage_kv <= thresholds['safe_max']
    
    def is_voltage_exceeds_threshold(self, node_id: str, voltage_kv: float) -> bool:
        """Check if voltage exceeds maximum allowed threshold"""
        thresholds = self.get_voltage_threshold(node_id)
        return voltage_kv > thresholds['safe_max']
    
    def get_node_statistics(self, node_id: str) -> Optional[Dict]:
        """Get statistics for a specific node"""
        history = self.history.get(node_id, [])
        
        if not history:
            return None
        
        # Calculate statistics from history
        powers = [h.get('active_power_mw', 0) for h in history[-100:]]
        voltages = [h.get('bus_voltage_kv', 0) for h in history[-100:]]
        
        if powers and voltages:
            return {
                'node_id': node_id,
                'power_avg_mw': sum(powers) / len(powers),
                'power_min_mw': min(powers),
                'power_max_mw': max(powers),
                'voltage_avg_kv': sum(voltages) / len(voltages),
                'voltage_min_kv': min(voltages),
                'voltage_max_kv': max(voltages),
                'sample_count': len(history)
            }
        
        return None
