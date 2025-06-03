"""
Main entry point for the application
"""
import sys
from ssm_manager.app import TrayIcon, ServerThread


def main(port: int = 5000) -> None:
    """
    Main entry point
    """
    if len(sys.argv) > 1 and sys.argv[1] == '--api':
        server = ServerThread()
        server.port = port
        server.debug = True
        server.run()
    else:
        tray = TrayIcon('static/favicon.ico',
                        server_port=port)
        tray.run()
    sys.exit(0)
