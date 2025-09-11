"""
Dependency management.
"""

# pylint: disable=logging-fstring-interpolation
import re
import logging
import subprocess
from urllib import request, error
from typing import Literal
from pydantic import BaseModel, ConfigDict
from ssm_manager.utils import CLIVersionCommand, SSMVersionCommand

logger = logging.getLogger(__name__)


class DependencyManager(BaseModel):
    """
    Manages dependencies for the project.
    """

    model_config = ConfigDict(strict=True)
    system: Literal["Linux", "Windows"]
    arch: Literal["x86_64", "AMD64"]
    message_not_installed: str = "Not Installed"
    message_unknown: str = "Unknown"

    @property
    def dependencies(self) -> dict:
        """
        Returns a dict of dependencies and their versions
        """
        return {
            "awscli": {
                "installed": self.awscli,
                "latest": self.awscli_latest_version,
                "urls": self.awscli_url,
            },
            "session_manager_plugin": {
                "installed": self.ssmplugin,
                "latest": self.ssmplugin_latest_version,
                "urls": self.ssmplugin_url,
            },
        }

    @property
    def installed(self) -> bool:
        """
        Returns True if all dependencies are installed
        """
        return all(
            version != self.message_not_installed
            for version in self.dependencies.values()
        )

    @property
    def awscli(self) -> str:
        """
        Returns the version of AWS CLI if installed
        """
        try:
            command = CLIVersionCommand(system=self.system)
            logger.info(f"Checking AWS CLI version with command: {command.cmd}")
            version = subprocess.run(
                command.cmd,
                startupinfo=command.startupinfo,
                capture_output=True,
                check=True,
            )
            if version.returncode == 0:
                match = re.search(
                    r"aws-cli\/([0-9\.]+)", version.stdout.decode("utf-8")
                )
                return match.group(1) if match else self.message_unknown
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("AWS CLI not found or error getting version.")
        return self.message_not_installed

    @property
    def awscli_url(self) -> list[str]:
        """
        Returns the download URL for AWS CLI based on the OS
        """
        base = "https://awscli.amazonaws.com"
        url = [{"link": f"{base}/AWSCLIV2.msi", "extension": "msi"}]
        if self.system == "Linux":
            url = [
                {"link": f"{base}/awscli-exe-linux-{self.arch}.zip", "extension": "zip"}
            ]
        return url

    @property
    def awscli_latest_version(self) -> str:
        """
        Returns the latest version of AWS CLI from GitHub Changelog
        """
        try:
            change_log_url = (
                "https://raw.githubusercontent.com/aws/aws-cli/v2/CHANGELOG.rst"
            )
            with request.urlopen(change_log_url) as response:
                if response.status != 200:
                    raise error.URLError(f"Error fetching changelog: {response.status}")
                changelog = response.read().decode("utf-8")
            pattern = re.compile(r"(\d{1,5}\.\d{1,5}\.\d{1,5})\n")
            match = pattern.search(changelog)
            if match:
                return match.group(1)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(f"Error fetching latest AWS CLI version: {e}")
        return self.message_unknown

    @property
    def ssmplugin(self) -> str:
        """
        Returns the version of Session Manager Plugin if installed
        """
        try:
            command = SSMVersionCommand(system=self.system)
            ssm = subprocess.run(
                command.cmd,
                startupinfo=command.startupinfo,
                capture_output=True,
                check=True,
            )
            if ssm.returncode == 0:
                return ssm.stdout.decode("utf-8").strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Session Manager Plugin not found or error getting version.")
        return self.message_not_installed

    @property
    def ssmplugin_url(self) -> list[str]:
        """
        Returns the download URL for the Session Manager Plugin based on the OS
        """
        base = "https://s3.amazonaws.com/session-manager-downloads/plugin/latest"
        url = [
            {
                "link": f"{base}/windows/SessionManagerPluginSetup.exe",
                "extension": "exe",
            }
        ]
        if self.system == "Linux":
            url = [
                {
                    "link": f"{base}/linux_64bit/session-manager-plugin.rpm",
                    "extension": "rpm",
                },
                {
                    "link": f"{base}/ubuntu_64bit/session-manager-plugin.deb",
                    "extension": "deb",
                },
            ]
        return url

    @property
    def ssmplugin_latest_version(self) -> str:
        """
        Returns the latest version of Session Manager Plugin from GitHub Releases
        """
        releases_url = (
            "https://api.github.com/repos/aws/session-manager-plugin/releases/latest"
        )
        try:
            with request.urlopen(releases_url) as response:
                if response.status != 200:
                    raise error.URLError(f"Error fetching releases: {response.status}")
                release_info = response.read().decode("utf-8")
            match = re.search(r'"tag_name":\s*"v?([0-9\.]+)"', release_info)
            if match:
                return match.group(1)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(f"Error fetching latest SSM Plugin version: {e}")
        return self.message_unknown
