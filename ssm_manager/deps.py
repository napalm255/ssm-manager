"""
Dependency management.
"""
# pylint: disable=logging-fstring-interpolation
import re
import logging
import subprocess
from typing import Optional, Literal, Any
from pydantic import (
    BaseModel, ConfigDict,
    computed_field
)
from ssm_manager.utils import CLIVersionCommand, SSMVersionCommand

logger = logging.getLogger(__name__)


class DependencyManager(BaseModel):
    """
    Manages dependencies for the project.
    """
    model_config = ConfigDict(strict=True)
    system: Literal["Linux", "Windows"]

    @property
    def dependencies(self) -> dict:
        """
        Returns a dict of dependencies and their versions
        """
        return {
            "awscli": self.awscli,
            "session_manager_plugin": self.ssmplugin
        }

    @property
    def installed(self) -> bool:
        """
        Returns True if all dependencies are installed
        """
        return all(version != "Not Installed" for version in self.dependencies.values())

    @property
    def awscli(self) -> str:
        """
        Returns the version of AWS CLI if installed
        """
        try:
            command = CLIVersionCommand(system=self.system)
            version = subprocess.run(command.cmd, capture_output=True, check=True)
            if version.returncode == 0:
                match = re.search(r'aws-cli\/([0-9\.]+)', version.stdout.decode('utf-8'))
                return match.group(1) if match else 'Unknown'
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("AWS CLI not found or error getting version.")
        return "Not Installed"

    @property
    def ssmplugin(self) -> str:
        """
        Returns the version of Session Manager Plugin if installed
        """
        try:
            command = SSMVersionCommand(system=self.system)
            ssm = subprocess.run(command.cmd, capture_output=True, check=True)
            if ssm.returncode == 0:
                return ssm.stdout.decode('utf-8').strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Session Manager Plugin not found or error getting version.")
        return "Not Installed"
