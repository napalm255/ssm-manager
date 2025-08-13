"""
AWS Config Manager
This module provides a class to manage AWS configuration files in a cross-platform manner.
It allows reading and writing values to the AWS config file, handling errors gracefully.
"""
# pylint: disable=logging-fstring-interpolation
import logging
import configparser
from pathlib import Path

logger = logging.getLogger(__name__)

class AwsConfigManager:
    """
    A class to read and write to the AWS config file in a cross-platform manner.
    """
    def __init__(self):
        """
        Initializes the manager by finding the AWS config file path.
        """
        self._config_path = self._get_aws_config_path()

    def _get_aws_config_path(self):
        """
        Determines the path to the AWS config file.
        This private method ensures the path is set correctly on init.

        Returns:
            pathlib.Path: The full path to the AWS config file.
        """
        home_dir = Path.home()
        aws_config_dir = home_dir / ".aws"
        aws_config_file = aws_config_dir / "config"
        return aws_config_file

    def read_value(self, section: str, key: str) -> str | None:
        """
        Reads a specific value from the AWS config file.

        Args:
            section (str): The section name (e.g., 'default' or 'profile myprofile').
            key (str): The key name (e.g., 'region').

        Returns:
            str or None: The value if found, otherwise None.
        """
        config = configparser.ConfigParser()

        # Check if the file exists before trying to read it
        if not self._config_path.is_file():
            logger.error(f"Error: AWS config file not found at {self._config_path}")
            return None

        try:
            config.read(self._config_path)
            if not config.has_section(section):
                raise ValueError(f"Section '{section}' not found in config file")
            if not config.has_option(section, key):
                raise ValueError(f"Key '{key}' not found in section '{section}'")

            return config.get(section, key)
        except ValueError as e:
            logger.error(f"Error reading config value: {e}")
            return None
        except configparser.Error as e:
            logger.error(f"Error reading config file: {e}")
            return None

    def write_value(self, section: str, key: str, value: str):
        """
        Writes a specific value to the AWS config file.
        If the section or file doesn't exist, it will be created.

        Args:
            section (str): The section name.
            key (str): The key name.
            value (str): The value to write.
        """
        config = configparser.ConfigParser()

        # Create the directory if it doesn't exist
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing config to not overwrite other settings
        if self._config_path.is_file():
            config.read(self._config_path)

        # Add or update the section and key
        if not config.has_section(section):
            config.add_section(section)

        config.set(section, key, value)

        try:
            with open(self._config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            logger.info(f"Successfully wrote '{value}' to section '{section}', key '{key}'")
        except IOError as e:
            logger.error(f"An I/O error occurred while writing to the file: {e}")

    def get_sessions(self) -> list[dict[str, str]]:
        """
        Lists all available sessions in the config file.

        Returns:
            list[dict[str, str]]: A list of dictionaries where each dictionary contains
            session properties like 'name', 'sso_start_url', 'sso_region', and
            'sso_registration_scopes'.
        """
        sessions = []
        try:
            session_names = []
            config = configparser.ConfigParser()
            if not self._config_path.is_file():
                raise ValueError(f"Error: AWS config file not found at {self._config_path}")

            config.read(self._config_path)
            for section in config.sections():
                if section.startswith('sso-session '):
                    session_names.append(section[len('sso-session '):])

            for name in session_names:
                section_name = 'sso-session ' + name
                session = {'name': name}
                for prop in ['sso_start_url', 'sso_region', 'sso_registration_scopes']:
                    if not config.has_option(section_name, prop):
                        logger.warning(f"Warning: '{prop}' not found in section '{section_name}'")
                        continue
                    session[prop] = config.get(section_name, prop, fallback=None)
                sessions.append(session)
        except configparser.Error as e:
            logger.error(f"Error reading sessions: {e}")
        except ValueError as e:
            logger.error(f"Error reading sessions: {e}")

        return sessions

    def add_session(self, name: str, start_url: str, region: str, registration_scopes: str):
        """
        Adds a new SSO session to the AWS config file.

        Args:
            name (str): The name of the session.
            start_url (str): The SSO start URL.
            region (str): The AWS region for the session.
            registration_scopes (str): The registration scopes for the session.
        """
        section_name = 'sso-session ' + name
        self.write_value(section_name, 'sso_start_url', start_url)
        self.write_value(section_name, 'sso_region', region)
        self.write_value(section_name, 'sso_registration_scopes', registration_scopes)

    def delete_session(self, name: str):
        """
        Deletes an SSO session from the AWS config file.

        Args:
            name (str): The name of the session to delete.
        """
        try:
            config = configparser.ConfigParser()
            if not self._config_path.is_file():
                raise ValueError(f"Error: AWS config file not found at {self._config_path}")

            config.read(self._config_path)
            section_name = 'sso-session ' + name
            assert config.has_section(section_name), f"Session '{name}' does not exist"

            config.remove_section(section_name)
            with open(self._config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            logger.info(f"Successfully deleted session '{name}'")
        except configparser.Error as e:
            logger.error(f"Error deleting session: {e}")
        except ValueError as e:
            logger.error(f"Error deleting session: {e}")
        except AssertionError as e:
            logger.warning(f"Error deleting session: {e}")


    def get_profiles(self) -> list[dict[str, str]]:
        """
        Lists all available profiles in the config file.

        Returns:
            list[dict[str, str]]: A list of dictionaries where each dictionary contains
            profile properties like 'name', 'region', 'output', 'sso_session', 'sso_account_id',
            and 'sso_role_name'.
        """
        profiles = []
        try:
            profile_names = []
            config = configparser.ConfigParser()
            if not self._config_path.is_file():
                raise ValueError(f"Error: AWS config file not found at {self._config_path}")

            config.read(self._config_path)
            for section in config.sections():
                if section.startswith('profile '):
                    profile_names.append(section[len('profile '):])
                elif section == 'default':
                    profile_names.append('default')

            for name in profile_names:
                section_name = 'profile ' + name if name != 'default' else 'default'
                profile = {'name': name}
                for prop in ['region', 'output', 'sso_session', 'sso_account_id', 'sso_role_name']:
                    if not config.has_option(section_name, prop):
                        logger.warning(f"Warning: '{prop}' not found in section '{section_name}'")
                        continue
                    profile[prop] = config.get(section_name, prop, fallback=None)
        except configparser.Error as e:
            logger.error(f"Error reading profiles: {e}")
        except ValueError as e:
            logger.error(f"Error reading profiles: {e}")
        return profiles

    def add_profile(self, name: str, **kwargs):
        """
        Adds a new profile to the AWS config file.

        Args:
            name (str): The name of the profile.
            region (str): The AWS region for the profile.
            output (str): The output format for the profile.
            session (str): The SSO session name for the profile.
            account_id (str): The SSO account ID for the profile.
            role_name (str): The SSO role name for the profile.
        """
        section_name = 'profile ' + name if name != 'default' else 'default'
        if not kwargs:
            logger.error("No properties provided to add to the profile.")
            return
        for prop in ['region', 'output', 'sso_session', 'sso_account_id', 'sso_role_name']:
            if prop not in kwargs:
                logger.warning(f"Warning: '{prop}' not provided for profile '{name}'")
                continue
            self.write_value(section_name, prop, str(kwargs[prop]))
        logger.info(f"Successfully added profile '{name}' with properties: {kwargs}")

    def delete_profile(self, name: str):
        """
        Deletes a profile from the AWS config file.
        Args:
            name (str): The name of the profile to delete.
        """
        try:
            config = configparser.ConfigParser()
            if not self._config_path.is_file():
                raise ValueError(f"Error: AWS config file not found at {self._config_path}")

            config.read(self._config_path)
            section_name = 'profile ' + name if name != 'default' else 'default'
            assert config.has_section(section_name), f"Profile '{name}' does not exist"

            config.remove_section(section_name)
            with open(self._config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            logger.info(f"Successfully deleted profile '{name}'")
        except configparser.Error as e:
            logger.error(f"Error deleting profile '{name}': {e}")
        except ValueError as e:
            logger.error(f"Error deleting profile: {e}")
        except AssertionError as e:
            logger.warning(f"Error deleting profile {e}")
