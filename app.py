"""
Application entry point
"""
import sys
import logging
import threading
import webview
from flask import Flask
from aws_manager import AWSManager


# Setup Flask
app = Flask(__name__)
app.debug = True
app.config['DEBUG'] = True
aws_manager = AWSManager()
# pylint: disable=wrong-import-position, wildcard-import, unused-wildcard-import
from routes import *

# Store active connections
active_connections = []

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Set specific log levels for different components
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


def run_server():
    """
    Run the Flask server
    """
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,  # With webview set False
        use_reloader=True
)


def create_application():
    """
    Create the application window
    """
    server = threading.Thread(target=run_server)
    server.daemon = True
    server.start()

    # Wait a bit for the server to start
    time.sleep(1)

    webview.create_window(
        title='SSM Manager',
        url='http://127.0.0.1:5000',
        width=1200,
        height=800,
        resizable=True
    )
    webview.start()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--apionly':
        run_server()
        sys.exit()
    create_application()
