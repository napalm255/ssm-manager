"""
Utilities for SSM-Manager.
"""
# pylint: disable=logging-fstring-interpolation
import logging
import shlex
import shutil
import subprocess
from time import time
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, ConfigDict
import boto3


logger = logging.getLogger(__name__)

UNSUPPORTED_SYSTEM = "Unsupported system type"


class Instance(BaseModel):
    """
    Model representing an instance with a name and ID.
    """
    name: Optional[str] = None
    id: str = Field(pattern=r"^i-[0-9a-f]{8,17}$")

    def get_name(self) -> str:
        return 'Testing'


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

    type: Literal["Shell", "RDP", "Custom Port", "Remote Host Port"] | None = None
    local_port: int | None = None
    remote_port: int | None = None
    remote_host: str | None = None

    def get(self, key: str, default=None):
        """
        Get the value of an attribute.
        """
        return getattr(self, key, default)

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
            self.name = self.name if self.name else connection.instance.id

            document_name = get_arg('--document-name')
            parameters = get_arg('--parameters')
            if parameters:
                params = {}
                for param in parameters.split(','):
                    key, value = param.split('=')
                    params[key] = value
                self.local_port = params.get('localPortNumber', None)
                if self.local_port:
                    self.local_port = int(self.local_port)
                self.remote_port = params.get('portNumber', None)
                if self.remote_port:
                    self.remote_port = int(self.remote_port)
                self.remote_host = params.get('host', None)
                if self.remote_host and self.remote_port:
                    self.type = 'Remote Host Port'
                if self.remote_port and not self.remote_host:
                    self.type = 'Custom Port'
                if self.remote_port == 3389:
                    self.type = 'RDP'

            if self.connection_id.startswith(('shell_', 'rdp_', 'port_')):
                conn_id = self.connection_id.split('_')
                if not self.type:
                    self.type = conn_id[0].upper()
                self.name = conn_id[1]
                self.timestamp = float(conn_id[-1])

            if not document_name and not parameters:
                self.type = 'Shell'
        except (ValueError, Exception):  # pylint: disable=broad-except
            return False


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
                return shlex.split(f'{remmina} -c rdp://localhost:{self.local_port} --no-tray-icon')
            raise ValueError("No linux RDP client found")
        if self.system == 'Windows':
            return f'mstsc /v:localhost:{self.local_port}'
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
