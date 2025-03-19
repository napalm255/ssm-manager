"""
SSM Manager
"""
import sys
import logging
import threading
import platform
import socket
import time
import shlex
import subprocess
import random
import uuid
import psutil
import webview
from preferences_handler import PreferencesHandler
from aws_manager import AWSManager
from cache import Cache
from flask import Flask, jsonify, request, render_template
# pylint: disable=logging-fstring-interpolation, line-too-long


# Setup cache
cache = Cache()

# Setup preferences
preferences_handler = PreferencesHandler()

# Setup Flask
app = Flask(__name__)
app.secret = b'_5#y2L"F4Q8z\n\xec]/'
app.debug = True
app.config['DEBUG'] = True

aws_manager = AWSManager()

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


@app.route('/api/profiles')
def get_profiles():
    """
    Endpoint to get available AWS profiles
    Returns: JSON list of profile names
    """
    try:
        logging.info("Attempting to load AWS profiles")
        profiles = aws_manager.get_profiles()
        return jsonify(profiles)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Failed to load AWS profiles: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to load profiles'}), 500

@app.route('/api/regions')
def get_regions():
    """
    Endpoint to get available AWS regions
    Returns: JSON list of region names
    """
    try:
        regions = aws_manager.get_regions()
        return jsonify(regions)
    except Exception as e:  # pylint: disable=broad-except
        return jsonify({"error": str(e)}), 500

@app.route('/api/connect', methods=['POST'])
def connect():
    """
    Endpoint to connect to AWS using the specified profile and region
    Returns: JSON response with status and account ID
    """
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')
        if not profile or not region:
            return jsonify({'error': 'Profile and region are required'}), 400
        aws_manager.set_profile_and_region(profile, region)
        aws_manager.list_ssm_instances()

        # Include account ID in the response
        return jsonify({
            'status': 'success',
            'account_id': aws_manager.account_id
        })
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Connection error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/instances')
def get_instances():
    """
    Endpoint to get a list of EC2 instances with SSM agent installed
    Returns: JSON list of instances
    """
    try:
        instances = aws_manager.list_ssm_instances()
        return jsonify(instances) if instances else jsonify([])
    except Exception as e:  # pylint: disable=broad-except
        return jsonify({"error": str(e)}), 500

@app.route('/api/ssh/<instance_id>', methods=['POST'])
def start_ssh(instance_id):
    """
    Endpoint to start an SSH session with an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    # pylint: disable=line-too-long
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')

        connection_id = f"ssh_{instance_id}_{int(time.time())}"

        cmd_exec = None
        cmd_run = None
        cmd_uuid = uuid.uuid4()
        cmd_aws = f'aws ssm start-session --target {instance_id} --region {region} --profile {profile} --reason {cmd_uuid}'
        if get_os() == 'Linux':
            cmd_exec = 'aws'
            cmd_run = f'gnome-terminal -- bash -c "{cmd_aws}"'
        elif get_os() == 'Windows':
            cmd_exec = 'aws.exe'
            cmd_run = f'start cmd /k {cmd_aws}'

        process = subprocess.Popen(cmd_run, shell=True)
        time.sleep(2)  # Wait for the process to start

        cmd_pid = get_pid(cmd_exec, cmd_aws)
        logging.debug(f"SSH process PID: {cmd_pid}")

        print(dir(process))
        connection = {
            'connection_id': connection_id,
            'instance_id': instance_id,
            'type': 'SSH',
            'process': process.pid,
            'profile': profile,
            'pid': cmd_pid,
            'timestamp': int(time.time()),
            'status': 'active'
        }
        print('*'*100)
        cache.append('active_connections', connection)

        thread = threading.Thread(
            target=monitor_process,
            args=(connection_id, cmd_pid),
            daemon=True
        )
        thread.start()

        logging.info(f"SSH session started - Instance: {instance_id}")
        return jsonify(connection)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error starting SSH: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rdp/<instance_id>', methods=['POST'])
def start_rdp(instance_id):
    """
    Start an RDP session with an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    # pylint: disable=line-too-long
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')

        connection_id = f"rdp_{instance_id}_{int(time.time())}"

        local_port = find_free_port()
        if local_port is None:
            logging.error("Could not find available port for RDP connection")
            return jsonify({'error': 'No available ports for RDP connection'}), 503

        logging.info(f"Starting RDP - Instance: {instance_id}, Port: {local_port}")

        cmd_exec = None
        cmd_run = None
        cmd_uuid = uuid.uuid4()
        cmd_aws = f"aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters portNumber=3389,localPortNumber={local_port} --region {region} --profile {profile} --reason {cmd_uuid}"
        if get_os() == 'Linux':
            cmd_exec = 'aws'
            cmd_run = cmd_aws
        elif get_os() == 'Windows':
            cmd_exec = 'aws.exe'
            cmd_aws = cmd_aws.replace('aws ', 'aws.exe ')
            cmd_run = f'powershell -Command "{cmd_aws}"'

        startupinfo = None
        if get_os() == 'Windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(shlex.split(cmd_run),
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)  # Wait for the process to start

        cmd_pid = get_pid(cmd_exec, cmd_aws)
        logging.debug(f"RDP process PID: {cmd_pid}")

        if get_os() == 'Windows':
            subprocess.Popen(f'mstsc /v:localhost:{local_port}')
        else:
            logging.warning("RDP is not supported on Linux")

        connection = {
            'connection_id': connection_id,
            'instance_id': instance_id,
            'type': 'RDP',
            'local_port': local_port,
            'process': process.pid,
            'profile': profile,
            'pid': cmd_pid,
            'timestamp': int(time.time()),
            'status': 'active'
        }
        cache.append('active_connections', connection)

        thread = threading.Thread(
            target=monitor_process,
            args=(connection_id, cmd_pid),
            daemon=True
        )
        thread.start()

        logging.info(f"RDP session started - Instance: {instance_id}, Port: {local_port}")
        return jsonify(connection)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error starting RDP: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/custom-port/<instance_id>', methods=['POST'])
def start_custom_port(instance_id):
    """
    Start custom port forwarding to an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    # pylint: disable=line-too-long
    try:
        data = request.json
        profile = data.get('profile')
        region = data.get('region')
        mode = data.get('mode', 'local')  # Default to local mode
        remote_port = data.get('remote_port')
        remote_host = data.get('remote_host')  # Will be None for local mode

        connection_id = f"port_{mode}_{instance_id}_{int(time.time())}"

        local_port = find_free_port()
        if local_port is None:
            logging.error("Could not find available port for port forwarding")
            return jsonify({'error': 'No available ports'}), 503

        cmd_exec = None
        cmd_run = None
        cmd_uuid = uuid.uuid4()
        if mode == 'local':
            logging.info(f"Starting local port forwarding - Instance: {instance_id}, Local: {local_port}, Remote: {remote_port}")
            cmd_aws = f"aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters portNumber={remote_port},localPortNumber={local_port} --region {region} --profile {profile} --reason {cmd_uuid}"
        else:
            logging.info(f"Starting remote host port forwarding - Instance: {instance_id}, Host: {remote_host}, Port: {remote_port}")
            cmd_aws = f"aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host={remote_host},portNumber={remote_port},localPortNumber={local_port} --region {region} --profile {profile} --reason {cmd_uuid}"

        if get_os() == 'Linux':
            cmd_exec = 'aws'
            cmd_run = cmd_aws
        elif get_os() == 'Windows':
            cmd_exec = 'aws.exe'
            cmd_aws = cmd_aws.replace('aws ', 'aws.exe ')
            cmd_run = f'powershell -Command "{cmd_aws}"'

        startupinfo = None
        if get_os() == 'Windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(shlex.split(cmd_run),
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(2)  # Wait for the process to start

        cmd_pid = get_pid(cmd_exec, cmd_aws)
        logging.debug(f"Port forwarding process PID: {cmd_pid}")

        # Create connection object with appropriate type and info
        connection = {
            'connection_id': connection_id,
            'instance_id': instance_id,
            'type': 'Custom Port' if mode == 'local' else 'Remote Host Port',
            'local_port': local_port,
            'remote_port': remote_port,
            'remote_host': remote_host if mode != 'local' else None,
            'process': process.pid,
            'profile': profile,
            'pid': cmd_pid,
            'timestamp': int(time.time()),
            'status': 'active'
        }
        cache.append('active_connections', connection)

        thread = threading.Thread(
            target=monitor_process,
            args=(connection_id, cmd_pid),
            daemon=True
        )
        thread.start()

        logging.info(f"Port forwarding started successfully - Mode: {mode}, Instance: {instance_id}")
        return jsonify(connection)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error starting port forwarding: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/instance-details/<instance_id>')
def get_instance_details(instance_id):
    """
    Get details of an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with instance details
    """
    try:
        logging.info(f"Get instance details: {instance_id}")
        details = aws_manager.get_instance_details(instance_id)
        if details is None:
            return jsonify({'error': 'Instance details not found'}), 404
        return jsonify(details)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error getting instance details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    """
    Get application preferences
    Returns: JSON response with preferences
    """
    try:
        return jsonify(preferences_handler.preferences)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error getting preferences: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/preferences', methods=['POST'])
def update_preferences():
    """
    Update application preferences
    Returns: JSON response with status
    """
    try:
        new_preferences = request.json
        if preferences_handler.update_preferences(new_preferences):
            return jsonify({'status': 'success'})
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error updating preferences: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """
    Refresh instance data
    Returns: JSON response with status and updated instance data
    """
    try:
        instances = aws_manager.list_ssm_instances()
        return jsonify({
            "status": "success",
            "instances": instances if instances else []
        })
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error refreshing data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/active-connections')
def get_active_connections():
    """
    Get active connections with port information
    Returns: JSON list of active connections
    """
    try:
        active = []
        to_remove = []

        for conn in cache.get('active_connections'):
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
                logging.error(f"Error checking connection: {str(e)}")
                to_remove.append(conn)

        for conn in to_remove:
            try:
                cache.remove('active_connections', conn)
            except ValueError:
                pass

        return jsonify(active)
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error getting active connections: {str(e)}")
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
        connection = next((c for c in cache.get('active_connections')
                           if c.get('connection_id') == connection_id), None)

        if not connection:
            return jsonify({"error": "Connection not found"}), 404

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

        return jsonify({"status": "success"})

    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error terminating connection: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/set-log-level', methods=['POST'])
def set_log_level():
    """
    Set the log level for the application
    Returns: JSON response with status
    """
    try:
        data = request.get_json()
        log_level = data.get('logLevel', 'INFO')

        numeric_level = getattr(logging, log_level.upper())

        logging.getLogger().setLevel(numeric_level)

        logging.getLogger('werkzeug').setLevel(numeric_level)
        return jsonify({'status': 'success'})
    except Exception as e:  # pylint: disable=broad-except
        logging.error(f"Error setting log level: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    """
    Home page route
    Returns: Rendered HTML template
    """
    return render_template('index.html')


def monitor_process(connection_id, pid):
    """
    Monitor the process and update the connection status
    Args:
        connection_id (str): Connection ID
        pid (int): Process ID
    """
    try:
        proc = psutil.Process(pid)
        proc.wait()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    finally:
        cache.get('active_connections')[:] = [c for c in cache.get('active_connections')
                                 if c['connection_id'] != connection_id]


def find_free_port():
    """
    Find a free port in the given range for AWS SSM port forwarding
    Returns: A free port number or None if no port is found
    """
    start_port, end_port = preferences_handler.get_port_range()
    logging.debug(f"Finding free port between {start_port} and {end_port}")
    start = start_port
    end = end_port
    max_attempts = 20
    logging.debug(f"Searching for free port between {start} and {end}")

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
                logging.info(f"Found free port: {port}")
                return port
            logging.debug(f"Port {port} is in use")
        except Exception as e:  # pylint: disable=broad-except
            logging.debug(f"Error checking port {port}: {str(e)}")
        finally:
            sock.close()
    logging.error(f"No free port found after {max_attempts} attempts")
    return None


def get_pid(executable, command):
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
            logging.error(f"Error getting PID for {executable} {command}")
            continue
    return None


def get_os():
    """
    Get the operating system name
    Returns:
        str: The operating system name
    """
    system = platform.system()
    if system not in ['Linux', 'Windows']:
        return 'Unsupported'
    return system


def run_server(debug=True):
    """
    Run the Flask server
    Note: When using webview, both debug and use_reloader must be set to False
    """
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=debug,
        use_reloader=debug
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
        run_server(debug=True)
    else:
        create_application()
