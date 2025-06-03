"""
Main entry point for the SSM Manager.
"""
import sys
from ssm_manager.utils import socket_is_open, open_browser

PORT = 5000

if __name__ == '__main__':
    if socket_is_open(PORT):
        print(f"Warning: SSM Manager is already running on port {PORT}.")
        open_browser(f'http://127.0.0.1:{PORT}')
        sys.exit(1)

    from ssm_manager.__main__ import main
    main(PORT)
