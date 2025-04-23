"""
Main entry point for the application
"""
import sys
from ssm_manager.app import TrayIcon, ServerThread, ConnectionMonitor


def main():
    """
    Main entry point
    """
    if len(sys.argv) > 1 and sys.argv[1] == '--api':
        server = ServerThread()
        server.debug = True
        server.run()
    else:
        tray = TrayIcon('static/favicon.ico')
        tray.run()
    sys.exit(0)
