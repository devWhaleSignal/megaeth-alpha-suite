#!/usr/bin/env python3
"""
Run the MegaETH Alpha Suite Web Dashboard
"""

import uvicorn
from web.server import app

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         MegaETH Alpha Suite - Web Dashboard              ║
    ║                                                          ║
    ║  🌐 Local:    http://localhost:8000                      ║
    ║  🌐 Network:  http://YOUR_IP:8000                        ║
    ║                                                          ║
    ║  Press CTRL+C to stop                                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        app, 
        host="0.0.0.0",  # Accessible from any IP
        port=8000,
        reload=False
    )
