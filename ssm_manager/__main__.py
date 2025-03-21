"""
Main entry point for the application
"""
import sys
from ssm_manager.app import create_tray, run_server


def main():
    """
    Main entry point
    """
    if len(sys.argv) > 1 and sys.argv[1] == '--api':
        run_server(debug=True)
    else:
        create_tray()
