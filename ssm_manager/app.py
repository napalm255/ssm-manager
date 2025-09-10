"""
SSM Manager
"""

import os
import re
import time
import subprocess
import psutil
import keyring
from flask import Flask, jsonify, request, render_template, send_file
from ssm_manager import (
    app_name,
    system,
    hosts_file,
    logger,
    cache,
    deps,
    aws_manager,
    preferences,
)
from ssm_manager.config import AwsConfigManager
from ssm_manager.utils import (
    Instance,
    Connection,
    ConnectionState,
    ConnectionScanner,
    AWSProfile,
    SSMCommand,
    SSOCommand,
    RDPCommand,
    CmdKeyAddCommand,
    CmdKeyDeleteCommand,
    HostsFileCommand,
    FreePort,
    run_cmd,
    resolve_hostname,
)

# pylint: disable=logging-fstring-interpolation, consider-using-with
# pylint: disable=too-many-lines

# Setup Flask
app = Flask(
    __name__, static_folder="static", static_url_path="/", template_folder="templates"
)


@app.route("/api/version")
def get_version():
    """
    Endpoint to get the version of the application
    Returns: JSON response with version information
    """
    version = {"name": app_name, "operating_system": system}
    try:
        version_file = os.path.join(os.path.dirname(__file__), "VERSION")
        with open(version_file, "r", encoding="utf-8") as vfile:
            version["version"] = vfile.read().strip()
        logger.info(f"Version: {version}")
    except FileNotFoundError:
        return logger.failed("Version file not found.")

    return jsonify(version)


@app.route("/api/dependencies")
def get_dependencies():
    """
    Endpoint to get the status of dependencies
    Returns: JSON response with dependency status
    """
    return jsonify(deps.dependencies)


@app.route("/api/profiles")
def get_profiles():
    """
    Endpoint to get available AWS profiles
    Returns: JSON list of profile names
    """
    profiles = aws_manager.get_profiles()
    logger.info(f"AWS profiles: {len(profiles)} found.")
    return jsonify(profiles)


@app.route("/api/regions")
def get_regions():
    """
    Endpoint to get available AWS regions
    Returns: JSON list of region names
    """
    preferences.reload_preferences()
    regions = preferences.get_regions()
    if not regions:
        regions = aws_manager.get_regions()
    logger.info(f"AWS Regions: {len(regions)} listed.")
    return jsonify(regions)


@app.route("/api/regions/all")
def get_all_regions():
    """
    Endpoint to get all AWS regions
    Returns: JSON list of all region names
    """
    regions = aws_manager.get_regions()
    logger.info(f"AWS Regions: {len(regions)} total.")
    return jsonify(regions)


@app.route("/api/config/sessions")
def get_config_sessions():
    """
    Endpoint to get AWS configuration sessions
    Returns: JSON list of AWS profiles from the configuration
    """
    config = AwsConfigManager()
    sessions = config.get_sessions()
    logger.info(f"Sessions: {len(sessions)} found.")
    return jsonify(sessions)


@app.route("/api/config/session", methods=["POST"])
def add_config_session():
    """
    Endpoint to add a new AWS configuration session
    Returns: JSON response with status
    """
    data = request.json

    # Validate required fields
    fields = ("name", "sso_start_url", "sso_region", "sso_registration_scopes")
    for field in fields:
        if not data.get(field, None):
            return logger.failed(f"Missing required field: {field}", 400)

    config = AwsConfigManager()
    config.add_session(
        name=data.get("name"),
        start_url=data.get("sso_start_url"),
        region=data.get("sso_region"),
        registration_scopes=data.get("sso_registration_scopes"),
    )

    session_exists = any(
        data["name"] == data.get("name") for data in config.get_sessions()
    )
    if not session_exists:
        return logger.failed(f"Failed to add session: {data.get('name')}")

    return logger.success(f"Session added successfully: {data.get('name')}")


@app.route("/api/config/session/<session_name>", methods=["DELETE"])
def delete_config_session(session_name):
    """
    Endpoint to delete an AWS configuration session
    Args:
        session_name (str): Name of the session to delete
    Returns: JSON response with status
    """
    config = AwsConfigManager()

    session_exists = any(data["name"] == session_name for data in config.get_sessions())
    if not session_exists:
        return logger.failed(f"Session '{session_name}' does not exist.", 404)

    config.delete_session(name=session_name)

    session_exists = any(data["name"] == session_name for data in config.get_sessions())
    if session_exists:
        return logger.failed(f"Failed to delete session: {session_name}")

    return logger.success(f"Session deleted successfully: {session_name}")


@app.route("/api/config/profile", methods=["POST"])
def add_config_profile():
    """
    Endpoint to add a new AWS configuration profile
    Returns: JSON response with status
    """
    data = request.json
    profile_name = data.get("name", None)

    # Validate required fields
    fields = (
        "name",
        "region",
        "sso_account_id",
        "sso_role_name",
        "sso_session",
        "output",
    )
    for field in fields:
        if not data.get(field, None):
            logger.failed(f"Missing required field: {field}", 400)

    config = AwsConfigManager()
    config.add_profile(
        name=profile_name,
        region=data.get("region", None),
        sso_account_id=data.get("sso_account_id", None),
        sso_role_name=data.get("sso_role_name", None),
        sso_session=data.get("sso_session", None),
        output=data.get("output", None),
    )

    profile_exists = any(
        data["name"] == profile_name for data in aws_manager.get_profiles()
    )
    if not profile_exists:
        return logger.failed(f"Failed to add profile: {profile_name}")

    return logger.success(f"Profile added successfully: {profile_name}")


@app.route("/api/config/profile/<profile_name>", methods=["DELETE"])
def delete_config_profile(profile_name):
    """
    Endpoint to delete an AWS configuration profile
    Args:
        profile_name (str): Name of the profile to delete
    Returns: JSON response with status
    """
    config = AwsConfigManager()
    profile_name = str(profile_name)

    profile_exists = any(
        data["name"] == profile_name for data in aws_manager.get_profiles()
    )
    if not profile_exists:
        return logger.failed(f"Profile '{profile_name}' does not exist.", 404)

    config.delete_profile(profile_name)

    profile_exists = any(
        data["name"] == profile_name for data in aws_manager.get_profiles()
    )
    if profile_exists:
        return logger.failed(f"Failed to delete profile: {profile_name}")

    return logger.success(f"Profile deleted successfully: {profile_name}")


@app.route("/api/config/hosts")
def get_config_hosts():
    """
    Endpoint to get system hosts file
    Returns: JSON list of hosts
    """
    hosts = []
    try:
        with open(hosts_file, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except FileNotFoundError:
        return logger.failed(f"Hosts file not found: {hosts_file}", 404)

    for line in lines:
        if line.strip() and line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            ip = parts[0]
            hostname = parts[1:]
            hosts.append({"ip": ip, "hostname": hostname})

    return jsonify(hosts)


@app.route("/api/config/host", methods=["POST"])
def update_config_hosts():
    """
    Endpoint to update system hosts file
    Returns: JSON response with status
    """
    if system != "Windows":
        return logger.failed(f"This feature is not supported on {system}.", 400)

    def host_ip_exists(hostname, ip):
        """Check if a hostname with the given IP exists in the hosts file."""
        pattern = re.compile(
            rf"^{re.escape(ip)}\s+{re.escape(hostname)}$", re.MULTILINE
        )
        with open(hosts_file, "r", encoding="utf-8") as file:
            content = file.read()
        return bool(pattern.search(content))

    data = request.json

    # Validate required fields
    fields = ("hostname", "ip")
    for field in fields:
        if not data.get(field, None):
            return logger.failed(f"Missing required field: {field}", 400)

    hostname = data["hostname"]
    ip = data["ip"]
    record = f"{ip}`t{hostname}"

    if host_ip_exists(hostname, ip):
        return logger.success(
            f"Host {hostname} with IP {ip} already exists in the hosts file."
        )

    hosts_file_escaped = hosts_file.replace(
        "\\", "\\\\"
    )  # Escape backslashes for Windows paths
    pscmd = f'(Add-Content -Path "{hosts_file_escaped}" -Value "{record}")'

    command = HostsFileCommand(runAs=True, command=pscmd)
    run_cmd(command, skip_pid_wait=True)
    added = False
    for _ in range(16):
        if resolve_hostname(hostname) != ip:
            time.sleep(0.25)
        else:
            added = True
            break
    if not added:
        return logger.failed(
            "Failed to add host to hosts file.<br>Host still resolvable."
        )

    return logger.success("Host added successfully")


@app.route("/api/config/host/<hostname>", methods=["DELETE"])
def delete_config_host(hostname):
    """
    Endpoint to delete a host from the system hosts file
    Args:
        hostname (str): Hostname to delete
    Returns: JSON response with status
    """
    if system != "Windows":
        return logger.failed(f"This feature is not supported on {system}.", 400)

    def host_exists(hostname):
        """Check if a hostname exists in the hosts file."""
        pattern = re.compile(rf"^[0-9]+.*{re.escape(hostname)}$", re.MULTILINE)
        with open(hosts_file, "r", encoding="utf-8") as file:
            content = file.read()
        return bool(pattern.search(content))

    if not host_exists(hostname):
        return logger.failed("Hostname not found in hosts file.")

    hosts_file_escaped = hosts_file.replace(
        "\\", "\\\\"
    )  # Escape backslashes for Windows paths
    pscmd = f'(Get-Content -Path "{hosts_file_escaped}")'
    pscmd += (
        " | Where-Object { $_ -notmatch ''^[0-9]+.*" + re.escape(hostname) + "$'' }"
    )
    pscmd += f' | Set-Content -Path "{hosts_file_escaped}"'

    command = HostsFileCommand(runAs=True, command=pscmd)
    run_cmd(command, skip_pid_wait=True)

    deleted = False
    for _ in range(16):
        if host_exists(hostname):
            time.sleep(0.25)
        else:
            deleted = True
            break
    if not deleted:
        return logger.failed(
            "Failed to delete host from hosts file.<br>Host still exists in the file."
        )

    return logger.success("Host deleted successfully")


@app.route("/api/config/credential", methods=["POST"])
def add_windows_credentials():
    """
    Endpoint to add Windows credentials
    Returns: JSON response with status
    """
    try:
        if system != "Windows":
            logger.failed(f"Windows credentials are not supported on {system}.")

        data = request.json

        instance = Instance(
            name=data.get("instance_name", None), id=data.get("instance_id", None)
        )
        username = data.get("username", None)
        local_port = data.get("local_port", None)

        if not (username and instance.name and instance.id and local_port):
            raise AssertionError(
                "Username, instance name, instance id, and local port are required."
            )

        password = keyring.get_password("ssm_manager", username)
        if not password:
            raise AssertionError(
                "Password not found in keyring for the provided username."
            )

        domain = ""
        if "\\" in username:
            domain, _ = username.split("\\", 1)
        targetname = f"{instance.name}.{domain}" if domain else instance.name
        targetname = f"{targetname}:{local_port}"

        command = CmdKeyAddCommand(
            targetname=targetname, username=username, password=password
        )
        run_cmd(command, skip_pid_wait=True)

        return logger.success(
            f"Windows Credentials added successfully for user: {username}"
        )
    except AssertionError as e:
        return logger.failed(f"Error: {str(e)}", 400)
    except Exception as e:  # pylint: disable=broad-except
        return logger.failed(f"Failed to add credentials: {str(e)}", 500)


@app.route("/api/config/credential", methods=["DELETE"])
def delete_windows_credentials():
    """
    Endpoint to delete Windows credentials
    Returns: JSON response with status
    """
    try:
        assert system == "Windows", "Windows credentials are only supported on Windows."

        data = request.json
        targetname = data.get("targetname", None)
        assert targetname is not None, "Target name is required."

        command = CmdKeyDeleteCommand(targetname=targetname)
        run_cmd(command, skip_pid_wait=True)

        return logger.success(
            f"Windows Credentials deleted successfully for target: {targetname}"
        )
    except AssertionError as e:
        return logger.failed(f"Error: {str(e)}", 400)
    except Exception as e:  # pylint: disable=broad-except
        return logger.failed(f"Failed to delete credentials: {str(e)}", 500)


@app.route("/api/connect", methods=["POST"])
def connect():
    """
    Endpoint to connect to AWS using the specified profile and region
    Returns: JSON response with status and account ID
    """
    data = request.json

    # Validate required fields
    for field in ("profile", "region"):
        if field not in data or not data.get(field, None):
            logger.failed(f"Missing required field: {field}", 400)

    profile = AWSProfile(name=data.get("profile"), region=data.get("region"))

    result = aws_manager.set_profile_and_region(profile.name, profile.region)
    max_retries = 2
    retries = 0
    delay = 1
    while not result and retries < max_retries:
        retries += 1
        logger.info(f"Starting SSO login with profile: {profile.name}")
        command = SSOCommand(
            region=profile.region,
            profile=profile.name,
            system=system,
            action="login",
            timeout=60,
        )
        run_cmd(command)
        result = aws_manager.set_profile_and_region(profile.name, profile.region)
        if not result:
            time.sleep(delay)

    logger.info(f"Connected to AWS - Profile: {profile.name}, Region: {profile.region}")
    return jsonify({"status": "success", "account_id": aws_manager.account_id})


@app.route("/api/instances")
def get_instances():
    """
    Endpoint to get a list of EC2 instances with SSM agent installed
    Returns: JSON list of instances
    """
    instances = aws_manager.list_ssm_instances()
    logger.info(f"Instances: {len(instances)} found.")
    return jsonify(instances)


@app.route("/api/shell/<instance_id>", methods=["POST"])
def start_shell(instance_id):
    """
    Endpoint to start an Shell session with an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    try:
        data = request.json

        profile = AWSProfile(name=data.get("profile"), region=data.get("region"))
        instance = Instance(name=data.get("name"), id=instance_id)
        connection = Connection(
            method="Shell", instance=instance, timestamp=time.time()
        )
        command = SSMCommand(
            instance=instance,
            region=profile.region,
            profile=profile.name,
            reason=connection,
            system=system,
            hide=False,
        )

        logger.info(f"Starting Shell - Instance: {instance.id}")
        pid = run_cmd(command)

        conn_state = ConnectionState(
            connection_id=str(connection),
            instance=instance,
            name=instance.name,
            type=connection.method,
            profile=command.profile,
            region=command.region,
            pid=pid,
            timestamp=connection.timestamp,
            status="active",
        )

        return jsonify(conn_state.dict())
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error starting Shell connection", 500)


@app.route("/api/rdp/<instance_id>", methods=["POST"])
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
        method = "RDP"

        profile = AWSProfile(name=data.get("profile"), region=data.get("region"))
        instance = Instance(name=data.get("name"), id=instance_id)
        connection = Connection(method=method, instance=instance, timestamp=time.time())

        remote_port = 3389
        local_port = FreePort(
            name=instance.name, remote_port=remote_port, preferences=preferences
        ).local_port

        if local_port is None:
            return logger.failed("No available ports for RDP connection", 503)

        command = SSMCommand(
            instance=instance,
            region=profile.region,
            profile=profile.name,
            reason=connection,
            system=system,
            hide=True,
            document_name="AWS-StartPortForwardingSession",
            remote_port=remote_port,
            local_port=local_port,
        )

        logger.info(
            f"Starting RDP session - Instance: {instance.id}, Port: {command.local_port}"
        )
        pid = run_cmd(command)

        logger.info("Opening RDP client...")
        open_rdp_client(command.local_port)

        conn_state = ConnectionState(
            connection_id=str(connection),
            instance=instance,
            name=instance.name,
            type=connection.method,
            profile=command.profile,
            region=command.region,
            pid=pid,
            timestamp=connection.timestamp,
            status="active",
            local_port=command.local_port,
        )

        return jsonify(conn_state.dict())
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error starting RDP connection", 500)


@app.route("/api/custom-port/<instance_id>", methods=["POST"])
def start_custom_port(instance_id):
    """
    Start custom port forwarding to an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with status and connection details
    """
    # pylint: disable=line-too-long, too-many-locals
    try:
        data = request.json
        mode = data.get("mode", "local")  # Default to local mode
        method = "PORT"

        profile = AWSProfile(name=data.get("profile"), region=data.get("region"))
        instance = Instance(name=data.get("name"), id=instance_id)
        connection = Connection(method=method, instance=instance, timestamp=time.time())

        remote_host = data.get("remote_host", None)
        remote_port = int(data.get("remote_port"))
        local_port = FreePort(
            name=instance.name,
            remote_port=remote_port,
            remote_host=remote_host,
            preferences=preferences,
        ).local_port

        if local_port is None:
            return logger.failed("No available ports for port forwarding")

        document_name = (
            "AWS-StartPortForwardingSessionToRemoteHost"
            if mode != "local"
            else "AWS-StartPortForwardingSession"
        )
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
            local_port=local_port,
        )

        logger.info(
            f"Starting {mode} port forwarding - Instance: {instance.id}, Local Port: {command.local_port}"
        )
        pid = run_cmd(command)

        conn_state = ConnectionState(
            connection_id=str(connection),
            instance=instance,
            name=instance.name,
            type="Custom Port" if mode == "local" else "Remote Host Port",
            profile=command.profile,
            region=command.region,
            pid=pid,
            timestamp=connection.timestamp,
            status="active",
            local_port=command.local_port,
            remote_port=command.remote_port,
            remote_host=command.remote_host if mode != "local" else None,
        )

        return jsonify(conn_state.dict())
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error starting port forwarding", 500)


@app.route("/api/instance-details/<instance_id>")
def get_instance_details(instance_id):
    """
    Get details of an EC2 instance
    Args:
        instance_id (str): ID of the EC2 instance
    Returns: JSON response with instance details
    """
    try:
        if not instance_id:
            return logger.failed("Instance ID is required", 400)
        instance = Instance(id=instance_id)

        details = aws_manager.get_instance_details(instance.id)
        if details is None:
            return logger.failed(f"Instance details not found: {instance.id}")

        return jsonify(details)
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error getting instance details", 500)


@app.route("/api/preferences")
def get_preferences():
    """
    Get application preferences
    Returns: JSON response with preferences
    """
    return jsonify(preferences.preferences)


@app.route("/api/preferences", methods=["POST"])
def update_preferences():
    """
    Update application preferences
    Returns: JSON response with status
    """
    try:
        assert preferences.update_preferences(request.json)
        logger.info("Preferences updated successfully")
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error updating preferences", 500)
    return jsonify({"status": "success"})


@app.route("/api/preferences/<instance_name>", methods=["POST"])
def update_instance_preferences(instance_name):
    """
    Update preferences for a specific instance
    Args:
        instance_name (str): Name of the instance
    Returns: JSON response with status
    """
    try:
        assert preferences.update_instance_preferences(instance_name, request.json)
        return logger.success("Preferences updated for instance")
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error updating preferences for instance", 500)


@app.route("/api/refresh")
def refresh_data():
    """
    Refresh instance data
    Returns: JSON response with status and updated instance data
    """
    try:
        instances = aws_manager.list_ssm_instances()
        return jsonify({"status": "success", "instances": instances})
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error refreshing data", 500)


@app.route("/api/active-connections")
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

        active_connections = cache.get("active_connections")
        assert active_connections is not None, "No active connections"

        for conn in active_connections:
            active.append(conn.dict())

        return jsonify(active)
    except AssertionError:
        return jsonify([])


@app.route("/api/terminate-connection/<connection_id>", methods=["POST"])
def terminate_connection(connection_id):
    """
    Terminate an active connection
    Args:
        connection_id (str): Connection ID
    Returns: JSON response with status
    """
    try:
        connection = None
        for conn in cache.get("active_connections"):
            if conn.connection_id == str(connection_id):
                connection = conn
                break

        if not connection:
            return logger.failed("Connection not found", 404)

        try:
            process = psutil.Process(connection.pid)
            for child in process.children(recursive=True):
                child.terminate()
            process.terminate()

            _, alive = psutil.wait_procs([process], timeout=3)
            for p in alive:
                p.kill()

            cache.remove("active_connections", connection)
            logger.info(f"Connection terminated: {connection}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return logger.success("Connection terminated")
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error terminating connection", 500)


@app.route("/api/rdp/<local_port>")
def open_rdp_client(local_port):
    """
    Open the RDP client with the specified local port
    Args:
        local_port (int): The local port to connect to
    """
    try:
        command = RDPCommand(local_port=local_port, system=system)
        subprocess.Popen(command.cmd)
        return logger.success("RDP client opened")
    except Exception:  # pylint: disable=broad-except
        return logger.failed("Error opening RDP client", 500)


@app.route("/")
def home():
    """
    Home page route
    Returns: Rendered HTML template
    """
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    """
    Favicon route
    Returns: Favicon image
    """
    return send_file("static/favicon.ico", mimetype="image/vnd.microsoft.icon")
