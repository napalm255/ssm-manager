"""
SSM Manager
"""
import os
import sys
import logging
import threading
import platform
import time
import subprocess
import psutil
import keyring
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from flask import Flask, jsonify, request, render_template, send_file
from ssm_manager.preferences import PreferencesHandler
from ssm_manager.manager import AWSManager
from ssm_manager.cache import Cache
from ssm_manager.utils import (
    Instance, Connection, ConnectionState, ConnectionScanner,
    AWSProfile, SSMCommand, SSOCommand, RDPCommand, CredCommand,
    run_cmd, FreePort, open_browser
)
# pylint: disable=logging-fstring-interpolation, line-too-long, consider-using-with

APP_NAME = 'SSM Manager'

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s:%(name)s - %(message)s',
    handlers=[
        logging.FileHandler('ssm_manager.log', mode='w'),
        logging.StreamHandler()
    ]
)

# Configure logger
logger = logging.getLogger('ssm_manager')

# Check if the system is Linux or Windows
system = platform.system()
if system not in ['Linux', 'Windows']:
    logger.critical("Unsupported operating system")
    sys.exit(1)

# Setup preferences
preferences = PreferencesHandler()

# Setup cache
cache = Cache()

# Setup Flask
app = Flask(__name__, static_folder='static', static_url_path='/', template_folder='templates')

aws_manager = AWSManager()


@app.route('/api/version')
def get_version():
    """
    Endpoint to get the version of the application
    Returns: JSON response with version information
    """
    try:
        logger.debug("Getting version...")
        version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
        version = {}
        with open(version_file, 'r', encoding='utf-8') as vfile:
            version = {
                'version': vfile.read().strip(),
                'name': APP_NAME,
                'operating_system': system,
            }
        logger.debug(f"Version: {version}")
        return jsonify(version)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error getting version: {str(e)}")
        return jsonify({'error': 'Error getting version'}), 500


@app.route('/api/profiles')
def get_profiles():
    """
    Endpoint to get available AWS profiles
    Returns: JSON list of profile names
    """
    try:
        profiles = aws_manager.get_profiles()
        logger.info(f"AWS profiles: {len(profiles)} found.")
        logger.debug(f"Profiles: {profiles}")
        return jsonify(profiles)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Failed to load AWS profiles: {str(e)}")
        return jsonify({'error': 'Failed to load profiles'}), 500


@app.route('/api/regions')
def get_regions():
    """
    Endpoint to get available AWS regions
    Returns: JSON list of region names
    """
    try:
        preferences.reload_preferences()
        regions = preferences.get_regions()
        if not regions:
            regions = aws_manager.get_regions()
        logger.info(f"AWS regions: {len(regions)} listed.")
        logger.debug(f"Regions: {regions}")
        return jsonify(regions)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Failed to load AWS regions: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load regions'}), 500


@app.route('/api/regions/all')
def get_all_regions():
    """
    Endpoint to get all AWS regions
    Returns: JSON list of all region names
    """
    try:
        regions = aws_manager.get_regions()
        logger.info(f"All AWS regions: {len(regions)}.")
        logger.debug(f"Regions: {regions}")
        return jsonify(regions)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Failed to load all AWS regions: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load all regions'}), 500


@app.route('/api/connect', methods=['POST'])
def connect():
    """
    Endpoint to connect to AWS using the specified profile and region
    Returns: JSON response with status and account ID
    """
    try:
        data = request.json
        profile = AWSProfile(
            name=data.get('profile'),
            region=data.get('region')
        )
        if not profile.name or not profile.region:
            logger.error("Failed to connect. Profile and region are required.")
            return jsonify({'error': 'Profile and region are required'}), 400

        try:
            logger.debug(f"Connecting to AWS - Profile: {profile.name}, Region: {profile.region}")
            aws_manager.set_profile_and_region(profile.name, profile.region)
        except ValueError:
            command = SSOCommand(region=profile.region,
                                 profile=profile.name,
                                 system=system,
                                 action='login',
                                 timeout=60)

            logger.info(f"Starting SSO login - Profile: {command.profile}")
            run_cmd(command)

            aws_manager.set_profile_and_region(command.profile, command.region)

        logger.info(f"Connected to AWS - Profile: {profile.name}, Region: {profile.region}")
        return jsonify({
            'status': 'success',
            'account_id': aws_manager.account_id
        })
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Connection error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Connection error'}), 500


@app.route('/api/instances')
def get_instances():
    """
    Endpoint to get a list of EC2 instances with SSM agent installed
    Returns: JSON list of instances
    """
    try:
        logger.debug("Loading EC2 instances...")
        instances = aws_manager.list_ssm_instances()
        logger.info(f"Successfully loaded {len(instances)} EC2 instances")
        return jsonify(instances)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Failed to load instances: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load instances'}), 500


@app.route('/api/shell/<instance_id>', methods=['POST'])
def start_shell(instance_id):
    """
    Endpoint to start an Shell session with an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    try:
        data = request.json

        profile = AWSProfile(
            name=data.get('profile'),
            region=data.get('region')
        )
        instance = Instance(
            name=data.get('name'),
            id=instance_id)
        connection = Connection(
            method='Shell',
            instance=instance,
            timestamp=time.time()
        )
        command = SSMCommand(
            instance=instance,
            region=profile.region,
            profile=profile.name,
            reason=connection,
            system=system,
            hide=False
        )

        logger.info(f"Starting Shell - Instance: {instance.id}")
        pid = run_cmd(command)

        conn_state = ConnectionState(
            connection_id = str(connection),
            instance = instance,
            name = instance.name,
            type = connection.method,
            profile = command.profile,
            region = command.region,
            pid = pid,
            timestamp = connection.timestamp,
            status = 'active'
        )

        logger.debug(f"Shell session started: {conn_state}")
        return jsonify(conn_state.dict())
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error starting Shell: {str(e)}")
        return jsonify({'error': f'Error starting Shell connection: {instance_id}'}), 500


@app.route('/api/rdp/<instance_id>', methods=['POST'])
def start_rdp(instance_id):
    """
    Start an RDP session with an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    # pylint: disable=line-too-long, too-many-locals
    try:
        data = request.json
        method = 'RDP'

        profile = AWSProfile(
            name=data.get('profile'),
            region=data.get('region')
        )
        instance = Instance(
            name=data.get('name'),
            id=instance_id
        )
        connection = Connection(
            method=method,
            instance=instance,
            timestamp=time.time()
        )

        remote_port = 3389
        local_port = FreePort(
            name=instance.name,
            remote_port=remote_port,
            preferences=preferences
        ).local_port

        if local_port is None:
            logger.error("Could not find available port for RDP connection")
            return jsonify({'error': 'No available ports for RDP connection'}), 503

        command = SSMCommand(
            instance=instance,
            region=profile.region,
            profile=profile.name,
            reason=connection,
            system=system,
            hide=True,
            document_name='AWS-StartPortForwardingSession',
            remote_port=remote_port,
            local_port=local_port
        )

        logger.info(f"Starting RDP session - Instance: {instance.id}, Port: {command.local_port}")
        pid = run_cmd(command)

        logger.info("Opening RDP client...")
        open_rdp_client(command.local_port)

        conn_state = ConnectionState(
            connection_id = str(connection),
            instance = instance,
            name = instance.name,
            type = connection.method,
            profile = command.profile,
            region = command.region,
            pid = pid,
            timestamp = connection.timestamp,
            status = 'active',
            local_port = command.local_port
        )

        logger.debug(f"RDP session started: {conn_state}")
        return jsonify(conn_state.dict())
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error starting RDP: {str(e)}")
        return jsonify({'error': 'Error starting RDP connection: {instance_id}'}), 500


@app.route('/api/custom-port/<instance_id>', methods=['POST'])
def start_custom_port(instance_id):
    """
    Start custom port forwarding to an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    # pylint: disable=line-too-long, too-many-locals
    try:
        logger.debug(f"Starting port forwarding - Instance: {instance_id}")
        data = request.json
        mode = data.get('mode', 'local')  # Default to local mode
        method = 'PORT'

        profile = AWSProfile(
            name=data.get('profile'),
            region=data.get('region')
        )
        instance = Instance(
            name=data.get('name'),
            id=instance_id
        )
        connection = Connection(
            method=method,
            instance=instance,
            timestamp=time.time()
        )

        remote_host = data.get('remote_host', None)
        remote_port = int(data.get('remote_port'))
        local_port = FreePort(
            name=instance.name,
            remote_port=remote_port,
            remote_host=remote_host,
            preferences=preferences
        ).local_port

        if local_port is None:
            logger.error("Could not find available port for port forwarding")
            return jsonify({'error': 'No available ports'}), 503

        try:
            username = data.get('username', None)
            if not username:
                raise ValueError("Username is required for credential configuration")

            password = keyring.get_password('ssm_manager', username)
            if not password:
                raise ValueError("Password not found in keyring for the provided username")

            logger.warning(f"Username: {username}, Password: {password}")

            command = CredCommand(
                instance=instance,
                local_port=local_port,
                system=system,
                username=username,
                password=password
            )
            logger.warning(f'Command {command}')
            run_cmd(command)
        except ValueError as e:
            logger.error(f"Failed to configure credentials: {str(e)}")

        document_name = 'AWS-StartPortForwardingSessionToRemoteHost' if mode != 'local' else 'AWS-StartPortForwardingSession'
        command = SSMCommand(
            instance=instance,
            region=profile.region,
            profile=profile.name,
            reason=connection,
            system=system,
            hide=True,
            document_name=document_name,
            remote_host=remote_host,
            remote_port=remote_port,
            local_port=local_port
        )

        logger.info(f"Starting {mode} port forwarding - Instance: {instance.id}, Local Port: {command.local_port}")
        pid = run_cmd(command)

        conn_state = ConnectionState(
            connection_id = str(connection),
            instance = instance,
            name = instance.name,
            type = 'Custom Port' if mode == 'local' else 'Remote Host Port',
            profile = command.profile,
            region = command.region,
            pid = pid,
            timestamp = connection.timestamp,
            status = 'active',
            local_port = command.local_port,
            remote_port = command.remote_port,
            remote_host = command.remote_host if mode != 'local' else None
        )

        logger.debug(f"Port forwarding session started: {conn_state}")
        return jsonify(conn_state.dict())
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error starting port forwarding: {str(e)}")
        return jsonify({'error': f'Error starting port forwarding: {instance_id}'}), 500


@app.route('/api/instance-details/<instance_id>')
def get_instance_details(instance_id):
    """
    Get details of an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with instance details
    """
    try:
        instance = Instance(id=instance_id)

        details = aws_manager.get_instance_details(instance.id)
        if details is None:
            logger.warning(f"Instance details not found: {instance.id}")
            return jsonify({'error': 'Instance details not found'}), 404

        logger.debug(f"Instance details: {details}")
        return jsonify(details)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error getting instance details: {str(e)}")
        return jsonify({'error': f'Error getting instance details: {instance_id}'}), 500


@app.route('/api/preferences')
def get_preferences():
    """
    Get application preferences
    Returns: JSON response with preferences
    """
    try:
        return jsonify(preferences.preferences)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error getting preferences: {str(e)}")
        return jsonify({'error': 'Error getting preferences'}), 500


@app.route('/api/preferences', methods=['POST'])
def update_preferences():
    """
    Update application preferences
    Returns: JSON response with status
    """
    try:
        assert preferences.update_preferences(request.json)
        logger.info("Preferences updated successfully")
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error updating preferences: {str(e)}")
        return jsonify({'error': 'Error updating preferences'}), 500
    return jsonify({'status': 'success'})


@app.route('/api/preferences/<instance_name>', methods=['POST'])
def update_instance_preferences(instance_name):
    """
    Update preferences for a specific instance
    Args:
        instance_name (str): Name of the instance
    Returns: JSON response with status
    """
    try:
        assert preferences.update_instance_preferences(instance_name, request.json)
        logger.info(f"Preferences updated for instance: {instance_name}")
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error updating instance preferences: {str(e)}")
        return jsonify({'error': f'Error updating preferences for instance: {instance_name}'}), 500
    return jsonify({'status': 'success'})

@app.route('/api/refresh')
def refresh_data():
    """
    Refresh instance data
    Returns: JSON response with status and updated instance data
    """
    try:
        instances = aws_manager.list_ssm_instances()
        logger.debug(f"Refreshing data - Instances: {len(instances)}")
        return jsonify({
            'status': 'success',
            'instances': instances
        })
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error refreshing data: {str(e)}")
        return jsonify({'error': 'Error refreshing data'}), 500


@app.route('/api/active-connections')
def get_active_connections():
    """
    Get active connections with port information
    Returns: JSON list of active connections
    """
    # pylint: disable=too-many-nested-blocks, too-many-branches
    try:
        active = []

        scanner = ConnectionScanner(cache)
        scanner.scan()

        active_connections = cache.get('active_connections')
        if not active_connections:
            logger.debug("No active connections found")
            return jsonify([])

        logger.debug(f"Active connections: {len(active_connections)}")
        for conn in active_connections:
            logger.debug(f"Active connection: {conn}")
            active.append(conn.dict())

        return jsonify(active)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error getting active connections: {str(e)}")
        return jsonify([])


@app.route('/api/terminate-connection/<connection_id>', methods=['POST'])
def terminate_connection(connection_id):
    """
    Terminate an active connection
    Args:
        connection_id (str): Connection ID
    Returns: JSON response with status
    """
    try:
        connection = None
        for conn in cache.get('active_connections'):
            if conn.connection_id == str(connection_id):
                connection = conn
                break

        if not connection:
            logger.warning("Unable to terminate. Connection not found.")
            return jsonify({"error": 'Connection not found'}), 404

        try:
            process = psutil.Process(connection.pid)
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()

            _, alive = psutil.wait_procs([process], timeout=3)
            for p in alive:
                p.kill()

            cache.remove('active_connections', connection)
            logger.info(f"Connection terminated: {connection}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return jsonify({'status': 'success'})
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error terminating connection: {str(e)}")
        return jsonify({'error': f'Error terminating connection: {connection_id}'}), 500


@app.route('/api/rdp/<local_port>')
def open_rdp_client(local_port):
    """
    Open the RDP client with the specified local port
    Args:
        local_port (int): The local port to connect to
    """
    logger.debug(f"Opening RDP client on port {local_port}")

    try:
        command = RDPCommand(local_port=local_port, system=system)
        subprocess.Popen(command.cmd)
        return jsonify({'status': 'success'})
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error opening rdp client: {str(e)}")
        return jsonify({'error': f'Error opening rdp client: {local_port}'}), 500


@app.route('/')
def home():
    """
    Home page route
    Returns: Rendered HTML template
    """
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    """
    Favicon route
    Returns: Favicon image
    """
    return send_file('static/favicon.ico', mimetype='image/vnd.microsoft.icon')


class ServerThread(threading.Thread):
    """
    Thread class for running the Flask server
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.daemon = True
        self.target = self.run
        self.debug = False
        self.port = 5000

    def stop(self):
        """
        Stop the server
        """
        self._stop_event.set()

    def stopped(self):
        """
        Check if the server is stopped
        """
        return self._stop_event.is_set()

    def run(self):
        """
        Run the server
        """
        while not self.stopped():
            logging.info("Starting server...")
            try:
                app.run(
                    host='127.0.0.1',
                    port=self.port,
                    debug=self.debug,
                    use_reloader=self.debug
                )
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f"Unexpected error: {str(e)}")
            finally:
                self.stop()
                logging.info("Exiting...")


class TrayIcon():
    """
    System tray icon class
    """
    def __init__(self, icon_file, **kwargs):
        self.server = ServerThread()
        self.server.port = kwargs.get('server_port', 5000)
        self.server.daemon = True
        self.icon = None
        self.icon_file = self.get_resource_path(icon_file)

    @property
    def image(self):
        """
        Load the icon image
        """
        try:
            image = Image.open(self.icon_file)
        except FileNotFoundError:
            logger.warning("Icon file not found, generating fallback image")
            image = self.create_icon(32, 32, 'black', 'white')
        return image

    @property
    def menu(self):
        """
        Create the system tray menu
        """
        return Menu(
            MenuItem('Open', self.open_app, default=True),
            MenuItem('Exit', self.exit_app)
        )

    def get_resource_path(self, relative_path):
        """
        Get absolute path to resource, works for dev and for PyInstaller
        Args:
            relative_path (str): Relative path to the resource
        Returns:
            str: Absolute path to the resource
        """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = os.path.join(sys._MEIPASS, 'ssm_manager')  # pylint: disable=protected-access
        except AttributeError:
            base_path = os.path.dirname(os.path.realpath(__file__))

        return os.path.join(base_path, relative_path)

    def create_icon(self, width, height, color1, color2):
        """
        Generates a simple fallback image
        Args:
            width (int): Image width
            height (int): Image height
            color1 (str): Background color
            color2 (str): Foreground color
        Returns:
            Image: The generated image
        """
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
        dc.rectangle((0, height // 2, width // 2, height), fill=color2)
        return image

    def exit_app(self, icon, item):
        """
        Exit the application
        """
        # pylint: disable=unused-argument
        logger.info("Exiting application...")
        self.server.stop()
        self.icon.stop()

    def open_app(self, *args):
        """
        Open the application in the default browser
        """
        # pylint: disable=unused-argument
        logger.info("Opening application...")
        open_browser(f'http://127.0.0.1:{self.server.port}/')

    def run(self):
        """
        Run the system tray icon
        """
        self.server.start()
        time.sleep(1)
        self.icon = Icon(APP_NAME, self.image, APP_NAME, menu=self.menu)
        self.open_app(None, None)
        if not self.server.stopped():
            self.icon.run()
