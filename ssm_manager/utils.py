"""
Utilities for SSM-Manager.
"""
# pylint: disable=logging-fstring-interpolation
import logging
import shlex
import shutil
import subprocess
import webbrowser
from time import sleep
from typing import Optional, Literal, Any
import socket
from random import randint
from pydantic import BaseModel, Field, ConfigDict
import psutil

logger = logging.getLogger(__name__)

UNSUPPORTED_SYSTEM = "Unsupported system type"


class AWSProfile(BaseModel):
    """
    Model representing an AWS Profile
    """
    name: str = Field(min_length=1)
    region: str = Field(pattern=r"^[a-z]{2}-[a-z]+-\d{1}$")


class Instance(BaseModel):
    """
    Model representing an instance with a name and ID.
    """
    name: Optional[str] = None
    id: str = Field(pattern=r"^i-[0-9a-f]{8,17}$")


class Connection(BaseModel):
    """
    Model representing a connection with a method and an Instance.
    """
    method: Literal["Shell", "RDP", "PORT", "MANUAL"]
    instance: Instance
    timestamp: float

    def __str__(self) -> str:
        name = self.instance.id
        if self.instance.name:
            name = f"{self.instance.name}_{self.instance.id}"
        return f"{self.method}_{name}_{self.timestamp}".lower()


class ConnectionState(BaseModel):
    """
    Model representing the state of a connection.
    """
    # pylint: disable=too-many-instance-attributes
    model_config = ConfigDict(strict=True)

    instance: Instance
    pid: int
    timestamp: float
    region: str | None = None
    profile: str | None = None
    connection_id: str | None = None
    name: str | None = None
    status: Literal["active", "inactive"] | None = None
    document_name: str | None = None

    type: Literal["Shell", "RDP", "Custom Port", "Remote Host Port"] | None = None
    local_port: int | None = None
    remote_port: int | None = None
    remote_host: str | None = None

    def get(self, key: str, default=None):
        """
        Get the value of an attribute.
        """
        return getattr(self, key, default)

    def _parse_params(self, params: str) -> dict:
        """
        Parse parameters from a string.
        """
        _params = {}
        for param in params.split(','):
            key, value = param.split('=')
            _params[key] = value

        self.local_port = _params.get('localPortNumber', None)
        if self.local_port:
            self.local_port = int(self.local_port)

        self.remote_port = _params.get('portNumber', None)
        if self.remote_port:
            self.remote_port = int(self.remote_port)

        self.remote_host = _params.get('host', None)

        if self.remote_port == 3389:
            self.type = 'RDP'
        elif self.remote_host and self.remote_port:
            self.type = 'Remote Host Port'
        elif self.remote_port and not self.remote_host:
            self.type = 'Custom Port'

        return _params

    def load(self, cmd: list) -> bool:
        """
        Load data into the model.
        """
        def get_arg(name: str, default: Any = None) -> str | None:
            try:
                return cmd[cmd.index(name) + 1]
            except (ValueError, IndexError):
                return default

        try:
            if '--target' not in cmd:
                raise ValueError("No instance id found")
            connection = Connection(
                method='MANUAL',
                instance=Instance(id=get_arg('--target')),
                timestamp=self.timestamp
            )
            self.status = 'active'
            self.connection_id = get_arg('--reason', str(connection))
            self.region = get_arg('--region', '')
            self.profile = get_arg('--profile', '')
            self.document_name = get_arg('--document-name')
            self.name = self.name if self.name else connection.instance.id

            parameters = get_arg('--parameters', None)
            if parameters:
                self._parse_params(parameters)

            if self.connection_id.startswith(('shell_', 'rdp_', 'port_')):
                conn_id = self.connection_id.split('_')
                if not self.type:
                    self.type = conn_id[0].upper()
                self.name = conn_id[1]
                self.timestamp = float(conn_id[-1])

            if not self.document_name and not parameters:
                self.type = 'Shell'
        except ValueError:
            return False


class ConnectionScanner():
    """
    Class to scan for active connections
    """
    def __init__(self, cache, interval=1):
        self.cache = cache
        self.interval = interval
        self.existing_pids = []

    def get_arg(self, cmd: str, name: str, default = None):
        """
        Get the argument from the command line
        Args:
            cmd (str): The command line
            name (str): The argument name
            default: Default value if not found
        Returns: The argument value or default
        """
        try:
            return cmd[cmd.index(name) + 1]
        except (ValueError, IndexError):
            return default

    def verify_pid(self, conn: Connection) -> bool:
        """
        Verify if a process with the given PID is running
        Args:
            pid (int): Process ID
            conn (Connection): Connection object
        Returns: True if the process is running, False otherwise
        """
        is_active = []
        try:
            process = psutil.Process(conn.pid)
            is_active.append(process.is_running())
            cmdline = process.cmdline()

            validate = [
                'ssm', 'start-session',
                conn.instance.id
            ]
            for item in validate:
                is_active.append(item in cmdline)

            if conn.local_port:
                is_active.append(socket_is_open(conn.local_port))
        except (KeyError, psutil.NoSuchProcess, psutil.AccessDenied):
            return False
        return all(is_active)


    def remove_inactive(self):
        """
        Remove inactive connections from the cache
        """
        active_connections = self.cache.get('active_connections')
        if not active_connections:
            return

        to_remove = []
        for conn in active_connections:
            try:
                if not self.verify_pid(conn):
                    to_remove.append(conn)
            except Exception as e:  # pylint: disable=broad-except
                logger.error(f"Error checking connection: {str(e)}")
                to_remove.append(conn)

        for conn in to_remove:
            try:
                self.cache.remove('active_connections', conn)
            except ValueError:
                pass

    def get_connections(self):
        """
        Get active connections
        Returns: A generator of ConnectionState objects
        """
        current_connections = self.cache.get('active_connections')
        if not current_connections:
            current_connections = []

        pids = [conn.pid for conn in current_connections]
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if proc.info['pid'] in pids:
                    continue
                if proc.name().lower() not in ('aws', 'aws.exe'):
                    continue
                logger.debug(f"Found a new process: {proc.info}")
                instance = Instance(
                    id=self.get_arg(proc.cmdline(), '--target')
                )
                connection_state = ConnectionState(
                    pid=int(proc.info['pid']),
                    instance=instance,
                    timestamp=proc.info['create_time']
                )
                connection_state.load(proc.cmdline())
                if connection_state in current_connections:
                    logger.warning(f"Connection already exists: {connection_state}")
                    continue
            except Exception as e:  # pylint: disable=broad-except
                logger.warning(f"Error checking process: {str(e)}")
                continue
            yield connection_state

    def scan(self):
        """
        Run the connection scan
        """
        self.remove_inactive()
        for connection in self.get_connections():
            self.cache.append('active_connections', connection)


class RDPCommand(BaseModel):
    """
    Model representing the RDP command.
    """
    local_port: int
    system: Literal["Linux", "Windows"]

    @property
    def cmd(self) -> str | list:
        """
        Build the command to run based on the system type.
        """
        if self.system == 'Linux':
            remmina = shutil.which("remmina")
            if remmina:
                return shlex.split(f'{remmina} -c rdp://127.0.0.1:{self.local_port} --no-tray-icon')
            raise ValueError("No linux RDP client found")
        if self.system == 'Windows':
            return f'mstsc /v:127.0.0.1:{self.local_port}'
        raise ValueError(UNSUPPORTED_SYSTEM)


class AWSCommand(BaseModel):
    """
    Model representing the AWS command.
    """
    region: str = Field(pattern=r"^[a-z]{2}-[a-z]+-\d{1}$")
    profile: str = Field(min_length=1)
    system: Literal["Linux", "Windows"]
    timeout: int | None = Field(default=None, ge=0)

    @property
    def startupinfo(self):
        """
        Return startupinfo for Windows.
        """
        if self.system == 'Windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            return startupinfo
        return None

    @property
    def exec(self) -> str:
        """
        Determine the executable based on the system type.
        """
        if self.system == 'Linux':
            return 'aws'
        if self.system == 'Windows':
            return 'aws.exe'
        raise ValueError(UNSUPPORTED_SYSTEM)

    @property
    def cmd(self) -> str | list:
        """
        Build the command to run based on the system type.
        """
        if self.system == 'Linux':
            if self.hide:
                return shlex.split(self._build_cmd())
            return f'gnome-terminal -- bash -c "{self._build_cmd()}"'
        if self.system == 'Windows':
            if self.hide:
                return shlex.split(f'powershell -Command "{self._build_cmd()}"')
            return f'start cmd /k {self._build_cmd()}'
        raise ValueError(UNSUPPORTED_SYSTEM)

    def __str__(self) -> str:
        return self._build_cmd()


class SSOCommand(AWSCommand):
    """
    Model representing the SSO command.
    """
    action: Literal["login", "logout"]
    hide: Optional[bool] = True
    wait: Optional[bool] = True

    def _build_cmd(self) -> str:
        """
        Build the command string.
        """
        cmd = [self.exec, 'sso', self.action,
               '--region', self.region,
               '--profile', self.profile]
        return str(' '.join(cmd))


class SSMCommand(AWSCommand):
    """
    Model representing the SSM command.
    """
    instance: Instance
    reason: Connection
    document_name: Optional[Literal["AWS-StartPortForwardingSession",
                                    "AWS-StartPortForwardingSessionToRemoteHost"]] = None
    local_port: Optional[int] = None
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None
    hide: Optional[bool] = True
    wait: Optional[bool] = False

    def _build_cmd(self) -> str:
        """
        Build the command string.
        """
        cmd = [self.exec, 'ssm', 'start-session',
               '--target', self.instance.id,
               '--region', self.region,
               '--profile', self.profile,
               '--reason', str(self.reason)]
        if self.document_name:
            cmd += ['--document-name', self.document_name]
        if self.local_port and self.remote_port and not self.remote_host:
            params = [f'portNumber={self.remote_port}',
                      f'localPortNumber={self.local_port}']
            cmd += ['--parameters', ','.join(params)]
        if self.local_port and self.remote_host and self.remote_port:
            params = [f'localPortNumber={self.local_port}',
                      f'host={self.remote_host}',
                      f'portNumber={self.remote_port}']
            cmd += ['--parameters', ','.join(params)]
        return str(' '.join(cmd))


class PSCommand(BaseModel):
    """
    Model representing the powershell command.
    Note: Windows only.
    """
    hide: Optional[bool] = True
    wait: Optional[bool] = True
    runAs: Optional[bool] = False
    timeout: int | None = Field(default=None, ge=0)

    @property
    def startupinfo(self):
        """
        Return startupinfo for Windows.
        """
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo

    @property
    def cmd(self) -> str | list:
        """
        Build the command to run based on the system type.
        """
        return shlex.split(f"powershell -Command '{self._build_cmd()}'")


class CmdKeyAddCommand(PSCommand):
    """
    Model representing the credential command.
    """
    targetname: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

    def _build_cmd(self) -> str:
        """
        Build the command string.
        """
        cmd = ['cmdkey.exe']
        cmd.extend([
            f'/add:"{self.targetname}"',
            f'/user:"{self.username}"',
            f'/pass:"{self.password}"'])
        return str(' '.join(cmd))


class CmdKeyDeleteCommand(PSCommand):
    """
    Model representing the credential delete command.
    """
    targetname: str = Field(min_length=1)

    def _build_cmd(self) -> str:
        """
        Build the command string.
        """
        cmd = ['cmdkey.exe']
        cmd.append(f'/delete:"{self.targetname}"')
        return str(' '.join(cmd))


class HostsFileCommand(PSCommand):
    """
    Model representing the powershell command
    """
    command: str

    def _build_cmd(self) -> str:
        """
        Build the command string.
        """
        cmd = ['Start-Process',
               'powershell.exe',
               f'-ArgumentList "{self.command}"'
        ]
        if self.hide:
            cmd.append('-WindowStyle Hidden')
        if self.runAs:
            cmd.append('-Verb RunAs')
        return str(' '.join(cmd))


class FreePort(BaseModel):
    """
    Class to find a free port
    """
    name: str
    remote_port: int
    remote_host: str | None = None
    preferences: Any = None
    start: int = Field(default=60000, ge=1024, le=65535)
    end: int = Field(default=65535, le=65535)

    @property
    def local_port(self) -> int | None:
        """
        Find a free port in the given range for AWS SSM port forwarding
        Returns: A free port number or None if no port is found
        """
        if self.preferences:
            self.start, self.end = self.preferences.get_port_range(
                self.name, self.remote_port, self.remote_host
            )
        max_attempts = 20

        used_ports = set()
        for _ in range(max_attempts):
            port = randint(self.start, self.end)

            if port in used_ports:
                continue

            used_ports.add(port)

            try:
                if not socket_is_open(port):
                    logger.info(f"Found free port: {port}")
                    return port
                logger.debug(f"Port {port} is in use")
            except Exception as e:  # pylint: disable=broad-except
                logger.error(f"Error checking port {port}: {str(e)}")
        logger.error(f"No free port found after {max_attempts} attempts")
        return None


def resolve_hostname(hostname: str) -> str | None:
    """
    Resolve a hostname to an IP address
    Args:
        hostname (str): The hostname to resolve
    Returns: The resolved IP address or the original hostname if resolution fails
    """
    try:
        ip_address = socket.gethostbyname(hostname)
        logger.debug(f"Resolved {hostname} to {ip_address}")
        return ip_address
    except socket.gaierror as e:
        logger.error(f"Failed to resolve {hostname}: {str(e)}")
    return None


def socket_is_open(port):
    """
    Check if a socket is open
    Args:
        host (str): Hostname or IP address
        port (int): Port number
    Returns: True if the socket is open, False otherwise
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error checking socket: {str(e)}")
        return False
    finally:
        sock.close()


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


def open_browser(url: str) -> None:
    """
    Open a url in the default browser
    Args:
        url (str): The URL to open
    Returns: None
    """
    webbrowser.open(url)


def run_cmd(cmd, skip_pid_wait=False, pid_max_retries=10, pid_retry_delay=2):
    """
    Run a shell command and return the pid
    Args:
        cmd (str): The command to run
    Returns:
        tuple: The process and the PID of the command
    """
    # pylint: disable=consider-using-with
    logger.debug(f"Running command: {cmd.cmd}")

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
    if not skip_pid_wait:
        retries = 0
        while not pid and retries < pid_max_retries:
            sleep(pid_retry_delay)
            pid = get_pid(str(cmd.exec), str(cmd))
            retries += 1

    if not skip_pid_wait and not pid:
        logger.error(f"Failed to get PID for command: {str(cmd)}")
        return None

    if cmd.wait:
        process.wait(timeout=cmd.timeout)

    return pid
