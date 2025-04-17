"""
SSM Manager
"""
import os
import sys
import signal
import logging
import webbrowser
import threading
import platform
import socket
import time
import subprocess
import random
import psutil
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from flask import Flask, jsonify, request, render_template, send_file
from ssm_manager.preferences import PreferencesHandler
from ssm_manager.manager import AWSManager
from ssm_manager.cache import Cache
from ssm_manager.utils import Instance, Connection, SSMCommand, SSOCommand, RDPCommand
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
app = Flask(__name__)

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
                'name': APP_NAME
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
        logger.debug("Loading AWS profiles...")
        profiles = aws_manager.get_profiles()
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
        logger.debug("Loading AWS regions...")
        preferences.reload_preferences()
        regions = preferences.get_regions()
        if not regions:
            regions = aws_manager.get_regions()
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
        logger.debug("Loading all AWS regions...")
        regions = aws_manager.get_regions()
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
        logger.debug("Connecting to AWS...")
        data = request.json
        profile = data.get('profile')
        region = data.get('region')

        if not profile or not region:
            return jsonify({'error': 'Profile and region are required'}), 400

        try:
            aws_manager.set_profile_and_region(profile, region)
        except ValueError:
            command = SSOCommand(region=region,
                                 profile=profile,
                                 system=system,
                                 action='login',
                                 timeout=60)

            logger.info(f"Starting SSO login - Profile: {command.profile}")
            run_cmd(command)

            aws_manager.set_profile_and_region(command.profile, command.region)

        logger.info(f"Connected to AWS - Profile: {profile}, Region: {region}")
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
        return jsonify(instances) if instances else jsonify([])
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Failed to load instances: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load instances'}), 500


@app.route('/api/ssh/<instance_id>', methods=['POST'])
def start_ssh(instance_id):
    """
    Endpoint to start an SSH session with an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    try:
        logger.debug(f"Starting SSH - Instance: {instance_id}")
        data = request.json
        method = 'SSH'

        instance = Instance(name=data.get('name'),
                            id=instance_id)
        connection = Connection(method=method,
                                instance=instance)
        command = SSMCommand(instance=instance,
                             region=data.get('region'),
                             profile=data.get('profile'),
                             reason=connection,
                             system=system,
                             hide=False)

        logger.info(f"Starting SSH - Instance: {instance.id}")
        pid = run_cmd(command)
        logger.debug(f"SSH process PID: {pid}")

        connection_state = {
            'connection_id': str(connection),
            'instance_id': instance.id,
            'name': instance.name,
            'type': connection.method,
            'profile': command.profile,
            'region': command.region,
            'pid': pid,
            'timestamp': int(time.time()),
            'status': 'active'
        }
        cache.append('active_connections', connection_state)

        logger.info(f"SSH session started - Instance: {instance.id}")
        return jsonify(connection_state)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error starting SSH: {str(e)}")
        return jsonify({'error': f'Error starting SSH connection: {instance_id}'}), 500


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
        logger.debug(f"Starting RDP - Instance: {instance_id}")
        data = request.json
        method = 'RDP'

        instance = Instance(name=data.get('name'),
                            id=instance_id)
        connection = Connection(method=method,
                                instance=instance)

        remote_port = 3389
        local_port = find_free_port(name=instance.name,
                                    remote_port=remote_port)
        if local_port is None:
            logger.error("Could not find available port for RDP connection")
            return jsonify({'error': 'No available ports for RDP connection'}), 503

        command = SSMCommand(instance=instance,
                             region=data.get('region'),
                             profile=data.get('profile'),
                             reason=connection,
                             system=system,
                             hide=True,
                             document_name='AWS-StartPortForwardingSession',
                             remote_port=remote_port,
                             local_port=local_port)

        logger.info(f"Starting RDP - Instance: {instance.id}, Port: {command.local_port}")
        pid = run_cmd(command)
        logger.debug(f"RDP process PID: {pid}")
        open_rdp_client(command.local_port)

        connection_state = {
            'connection_id': str(connection),
            'instance_id': instance.id,
            'name': instance.name,
            'type': connection.method,
            'local_port': command.local_port,
            'profile': command.profile,
            'region': command.region,
            'pid': pid,
            'timestamp': connection.time,
            'status': 'active'
        }
        cache.append('active_connections', connection_state)

        logger.info(f"RDP session started - Instance: {instance.id}, Port: {local_port}")
        return jsonify(connection_state)
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

        instance = Instance(name=data.get('name'),
                            id=instance_id)
        connection = Connection(method=method,
                                instance=instance)


        remote_host = data.get('remote_host', None)
        remote_port = int(data.get('remote_port'))
        local_port = find_free_port(name=instance.name,
                                    remote_port=remote_port,
                                    remote_host=remote_host)
        if local_port is None:
            logger.error("Could not find available port for port forwarding")
            return jsonify({'error': 'No available ports'}), 503

        document_name = 'AWS-StartPortForwardingSessionToRemoteHost' if mode != 'local' else 'AWS-StartPortForwardingSession'
        command = SSMCommand(instance=instance,
                             region=data.get('region'),
                             profile=data.get('profile'),
                             reason=connection,
                             system=system,
                             hide=True,
                             document_name=document_name,
                             remote_host=remote_host,
                             remote_port=remote_port,
                             local_port=local_port)

        logger.info(f"Starting {mode} port forwarding - Instance: {instance.id}, Local Port: {command.local_port}, Remote Host: {command.remote_host}, Remote Port: {command.remote_port}")
        pid = run_cmd(command)
        logger.debug(f"Port forwarding process PID: {pid}")

        connection_state = {
            'connection_id': str(connection),
            'instance_id': instance.id,
            'name': instance.name,
            'type': 'Custom Port' if mode == 'local' else 'Remote Host Port',
            'local_port': command.local_port,
            'remote_port': command.remote_port,
            'remote_host': command.remote_host if mode != 'local' else None,
            'profile': command.profile,
            'region': command.region,
            'pid': pid,
            'timestamp': connection.time,
            'status': 'active'
        }
        cache.append('active_connections', connection_state)

        logger.info(f"Port forwarding started successfully - Mode: {mode}, Instance: {instance.id}")
        return jsonify(connection_state)
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
        logger.debug(f"Getting instance details - Instance: {instance.id}")
        details = aws_manager.get_instance_details(instance.id)
        if details is None:
            return jsonify({'error': 'Instance details not found'}), 404
        return jsonify(details)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error getting instance details: {str(e)}")
        return jsonify({'error': f'Error getting instance details: {instance_id}'}), 500


@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    """
    Get application preferences
    Returns: JSON response with preferences
    """
    try:
        logger.debug("Getting preferences...")
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
        logger.debug("Updating preferences...")
        new_preferences = request.json
        preferences.update_preferences(new_preferences)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error updating preferences: {str(e)}")
        return jsonify({'error': 'Error updating preferences'}), 500
    return jsonify({'status': 'success'})


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """
    Refresh instance data
    Returns: JSON response with status and updated instance data
    """
    try:
        logger.debug("Refreshing data...")
        instances = aws_manager.list_ssm_instances()
        return jsonify({
            'status': 'success',
            'instances': instances if instances else []
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
        logger.debug("Getting active connections...")
        active = []
        to_remove = []

        active_connections = cache.get('active_connections')
        if not active_connections:
            return jsonify([])

        for conn in active_connections:
            try:
                is_active = False
                pid = conn.get('pid')

                if pid:
                    try:
                        process = psutil.Process(pid)
                        if process.is_running():
                            if conn['type'] in ['RDP', 'Custom Port']:
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                try:
                                    result = sock.connect_ex(('127.0.0.1', conn['local_port']))
                                    is_active = result == 0
                                finally:
                                    sock.close()
                            else:
                                is_active = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                if is_active:
                    active.append(conn)
                else:
                    to_remove.append(conn)
            except Exception as e:  # pylint: disable=broad-except
                logger.error(f"Error checking connection: {str(e)}")
                to_remove.append(conn)

        for conn in to_remove:
            try:
                cache.remove('active_connections', conn)
            except ValueError:
                pass

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
        logger.debug(f"Terminating connection - ID: {connection_id}")
        connection = next((c for c in cache.get('active_connections')
                           if c.get('connection_id') == connection_id), None)

        if not connection:
            return jsonify({"error": 'Connection not found'}), 404

        pid = connection.get('pid')
        if pid:
            try:
                process = psutil.Process(pid)
                for child in process.children(recursive=True):
                    child.terminate()
                process.terminate()

                _, alive = psutil.wait_procs([process], timeout=3)
                for p in alive:
                    p.kill()

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        cache.get('active_connections')[:] = [c for c in cache.get('active_connections')
                                 if c.get('connection_id') != connection_id]

        return jsonify({'status': 'success'})
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error terminating connection: {str(e)}")
        return jsonify({'error': f'Error terminating connection: {connection_id}'}), 500


@app.route('/api/rdp/<local_port>', methods=['GET'])
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


def find_free_port(name: str, remote_port: int, remote_host: str = None):
    """
    Find a free port in the given range for AWS SSM port forwarding
    Returns: A free port number or None if no port is found
    """
    start_port, end_port = preferences.get_port_range(name, remote_port, remote_host)
    logger.debug(f"Finding free port between {start_port} and {end_port}")
    start = start_port
    end = end_port
    max_attempts = 20

    used_ports = set()
    for _ in range(max_attempts):
        port = random.randint(start, end)

        if port in used_ports:
            continue

        used_ports.add(port)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()

            if result != 0:  # Port is available
                logger.info(f"Found free port: {port}")
                return port
            logger.debug(f"Port {port} is in use")
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error checking port {port}: {str(e)}")
        finally:
            sock.close()
    logger.error(f"No free port found after {max_attempts} attempts")
    return None


def get_pid(executable: str, command: str):
    """
    Get the PID of a process by executable and command
    Args:
        cmd_executable (str): The executable name
        cmd_command (str): The command to search for
    Returns:
        int: The PID of the process
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.name().lower() == executable:
                cmdline = ' '.join(proc.cmdline()).lower()
                if command.lower() in cmdline:
                    return proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.error(f"Error getting PID for {executable} {command}")
            continue
    return None


def run_cmd(cmd):
    """
    Run a shell command and return the pid
    Args:
        cmd (str): The command to run
    Returns:
        tuple: The process and the PID of the command
    """
    logger.debug(f"Running command: {cmd.cmd}")

    print(cmd.timeout)
    process = None
    if cmd.hide:
        process = subprocess.Popen(cmd.cmd,
            startupinfo=cmd.startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    else:
        process = subprocess.Popen(cmd.cmd, shell=True)

    pid = None
    max_retries = 10
    retries = 0
    while not pid and retries < max_retries:
        time.sleep(2)
        pid = get_pid(str(cmd.exec), str(cmd))
        retries += 1

    if not pid:
        logger.error(f"Failed to get PID for command: {str(cmd)}")
        return None

    if cmd.wait:
        process.wait(timeout=cmd.timeout)

    return pid


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
            app.run(
                host='127.0.0.1',
                port=5000,
                debug=self.debug,
                use_reloader=self.debug
            )
            self.stop()
        logging.info("Server stopped")


class TrayIcon():
    """
    System tray icon class
    """
    def __init__(self, icon_file):
        self.server = ServerThread()
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
        # pid = os.getpid()
        # if pid:
        #     os.kill(pid, signal.SIGTERM)

    def open_app(self, icon, item):
        """
        Open the application in the default browser
        """
        # pylint: disable=unused-argument
        logger.info("Opening application...")
        webbrowser.open('http://localhost:5000')

    def run(self):
        """
        Run the system tray icon
        """
        self.server.start()
        time.sleep(1)
        self.open_app(None, None)
        self.icon = Icon(APP_NAME, self.image, APP_NAME, menu=self.menu)
        self.icon.run()
