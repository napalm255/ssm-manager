"""
Utilities for SSM-Manager.
"""
import subprocess
from time import time
from typing import Optional, Literal
from pydantic import BaseModel, constr


class Instance(BaseModel):
    """
    Model representing an instance with a name and ID.
    """
    name: Optional[str] = None
    id: constr(pattern=r"^i-[0-9a-f]{8,17}$")


class Connection(BaseModel):
    """
    Model representing a connection with a method and an Instance.
    """
    method: Literal["SSH", "RDP", "PORT"]
    instance: Instance
    time: int = time()

    def __str__(self) -> str:
        name = self.instance.id
        if self.instance.name:
            name = f"{self.instance.name}_{self.instance.id}"
        return f"{self.method}_{name}_{self.time}"


class SSOCommand(BaseModel):
    """
    Model representing the SSO command.
    """
    region: constr(pattern=r"^[a-z]{2}-[a-z]+-\d{1}$")
    profile: str
    system: Literal["Linux", "Windows"]
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
        raise ValueError("Unsupported system type")

    @property
    def cmd(self) -> str:
        """
        Build the command to run based on the system type.
        """
        if self.system == 'Linux':
            if self.hide:
                return self._build_cmd()
            return f'gnome-terminal -- bash -c "{self._build_cmd()}"'
        if self.system == 'Windows':
            if self.hide:
                return f'powershell -Command "{self._build_cmd()}"'
            return f'start cmd /k {self._build_cmd()}'
        raise ValueError("Unsupported system type")

    def __str__(self) -> str:
        return self._build_cmd()


class SSMCommand(BaseModel):
    """
    Model representing the SSM command.
    """
    instance: Instance
    region: constr(pattern=r"^[a-z]{2}-[a-z]+-\d{1}$")
    profile: str
    reason: Connection
    system: Literal["Linux", "Windows"]
    document_name: Optional[Literal["AWS-StartPortForwardingSession",
                                    "AWS-StartPortForwardingSessionToRemoteHost"]] = None
    local_port: Optional[int] = None
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None
    hide: bool = False
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
        raise ValueError("Unsupported system type")

    @property
    def cmd(self) -> str:
        """
        Build the command to run based on the system type.
        """
        if self.system == 'Linux':
            if self.hide:
                return self._build_cmd()
            return f'gnome-terminal -- bash -c "{self._build_cmd()}"'
        if self.system == 'Windows':
            if self.hide:
                return f'powershell -Command "{self._build_cmd()}"'
            return f'start cmd /k {self._build_cmd()}'
        raise ValueError("Unsupported system type")

    def __str__(self) -> str:
        return self._build_cmd()
