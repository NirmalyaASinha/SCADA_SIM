"""
Node Registry
Tracks all registered SCADA nodes and their status
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NodeRegistry:
    """
    Registry of all SCADA nodes
    Tracks registration, heartbeats, and status
    """
    
    def __init__(self):
        # Registered nodes: node_id -> node_info
        self.nodes: Dict[str, Dict] = {}
        
        # Heartbeat tracking
        self.heartbeat_timeout = 30  # seconds
        
        logger.info("Node registry initialized")
    
    def register_node(self, node_info: Dict) -> Dict:
        """
        Register a new node or update existing registration
        
        Args:
            node_info: Dict with node_id, node_type, ip, ports, etc.
        
        Returns: Registration result
        """
        node_id = node_info['node_id']
        
        # Check if node exists
        is_new = node_id not in self.nodes
        
        # Store/update node info
        self.nodes[node_id] = {
            **node_info,
            'registered_at': datetime.utcnow().isoformat(),
            'last_heartbeat': datetime.utcnow().isoformat(),
            'status': 'ONLINE',
            'heartbeat_count': 0
        }
        
        if is_new:
            logger.info(f"New node registered: {node_id} ({node_info['node_type']}) at {node_info['ip']}")
        else:
            logger.info(f"Node re-registered: {node_id}")
        
        return {
            'status': 'registered',
            'node_id': node_id,
            'is_new': is_new
        }
    
    def heartbeat(self, node_id: str) -> bool:
        """
        Process heartbeat from a node
        
        Args:
            node_id: Node identifier
        
        Returns: True if successful, False if node not registered
        """
        if node_id not in self.nodes:
            logger.warning(f"Heartbeat from unregistered node: {node_id}")
            return False
        
        # Update heartbeat timestamp
        self.nodes[node_id]['last_heartbeat'] = datetime.utcnow().isoformat()
        self.nodes[node_id]['heartbeat_count'] += 1
        
        # Update status if was offline
        if self.nodes[node_id]['status'] in ['OFFLINE', 'DEGRADED']:
            logger.info(f"Node {node_id} back online")
            self.nodes[node_id]['status'] = 'ONLINE'
        
        return True
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get node information"""
        return self.nodes.get(node_id)
    
    def get_all_nodes(self) -> List[Dict]:
        """Get all registered nodes"""
        return list(self.nodes.values())
    
    def update_node_status(self, node_id: str, status: str):
        """Update node status"""
        if node_id in self.nodes:
            old_status = self.nodes[node_id]['status']
            self.nodes[node_id]['status'] = status
            
            if old_status != status:
                logger.info(f"Node {node_id} status changed: {old_status} -> {status}")
    
    def check_heartbeats(self):
        """
        Check all nodes for missed heartbeats
        Called periodically by admin service
        """
        now = datetime.utcnow()
        timeout = timedelta(seconds=self.heartbeat_timeout)
        
        for node_id, node_info in self.nodes.items():
            last_heartbeat = datetime.fromisoformat(node_info['last_heartbeat'])
            time_since_heartbeat = now - last_heartbeat
            
            if time_since_heartbeat > timeout:
                if node_info['status'] != 'OFFLINE':
                    logger.warning(
                        f"Node {node_id} appears offline "
                        f"(last seen {time_since_heartbeat.seconds}s ago)"
                    )
                    self.update_node_status(node_id, 'OFFLINE')
    
    def get_online_count(self) -> int:
        """Get count of online nodes"""
        return sum(1 for node in self.nodes.values() if node['status'] == 'ONLINE')
    
    def get_total_count(self) -> int:
        """Get total registered node count"""
        return len(self.nodes)
