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
