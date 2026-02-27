"""
Startup Connection Dialog
Prompts operator for SCADA Master IP address on node startup
"""

import sys
import os
from typing import Tuple


def run_startup_dialog(node_id: str) -> Tuple[str, int]:
    """
    Display startup dialog and get master connection info
    
    Args:
        node_id: Node identifier
    
    Returns:
        Tuple of (master_ip, master_port)
    """
    
    # Check if auto-connect mode (Docker)
    auto_connect = os.getenv('AUTO_CONNECT', 'false').lower() == 'true'
    
    if auto_connect:
        # Use environment variables directly
        master_ip = os.getenv('MASTER_IP', 'admin_service')
        master_port = int(os.getenv('MASTER_PORT', '9000'))
        print(f"Auto-connect mode: {master_ip}:{master_port}")
        return master_ip, master_port
    
    # Display startup banner
    print("\n")
    print("╔════════════════════════════════════════╗")
    print(f"║   SCADA NODE STARTUP -- {node_id:8s}     ║")
    print("╠════════════════════════════════════════╣")
    print("║  Connect to which SCADA Master?        ║")
    print("║                                        ║")
    print("║  [1] Localhost  (127.0.0.1:9000)       ║")
    print("║  [2] Custom IP  (enter manually)       ║")
    print("║                                        ║")
    print("║  Enter choice (1 or 2):                ║")
    print("╚════════════════════════════════════════╝")
    print()
    
    # Get user choice
    while True:
        try:
            choice = input("Enter choice (1 or 2): ").strip()
            
            if choice == '1':
                master_ip = '127.0.0.1'
                master_port = 9000
                break
            
            elif choice == '2':
                print()
                master_ip = input("Enter SCADA Master IP address: ").strip()
                
                # Validate IP format (basic check)
                parts = master_ip.split('.')
                if len(parts) != 4:
                    print("❌ Invalid IP address format. Please try again.")
                    continue
                
                try:
                    for part in parts:
                        if not (0 <= int(part) <= 255):
                            raise ValueError()
                except ValueError:
                    print("❌ Invalid IP address format. Please try again.")
                    continue
                
                port_input = input("Enter SCADA Master port [9000]: ").strip()
                if port_input:
                    try:
                        master_port = int(port_input)
                        if not (1 <= master_port <= 65535):
                            raise ValueError()
                    except ValueError:
                        print("❌ Invalid port number. Please try again.")
                        continue
                else:
                    master_port = 9000
                
                break
            
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
        
        except KeyboardInterrupt:
            print("\n\n❌ Startup cancelled by user.")
            sys.exit(1)
        except EOFError:
            print("\n\n❌ Unexpected end of input.")
            sys.exit(1)
    
    print()
    print(f"✅ Will connect to SCADA Master at {master_ip}:{master_port}")
    print()
    
    return master_ip, master_port
