"""
AWS Config Manager
This module provides a class to manage AWS configuration files in a cross-platform manner.
It allows reading and writing values to the AWS config file, handling errors gracefully.
"""

import os
import configparser
from pathlib import Path

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
            print(f"Error: AWS config file not found at {self._config_path}")
            return None

        try:
            config.read(self._config_path)
            if config.has_section(section):
                if config.has_option(section, key):
                    return config.get(section, key)
                else:
                    print(f"Key '{key}' not found in section '{section}'")
                    return None
            else:
                print(f"Section '{section}' not found in config file")
                return None
        except configparser.Error as e:
            print(f"An error occurred while parsing the config file: {e}")
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
            with open(self._config_path, 'w') as configfile:
                config.write(configfile)
            print(f"Successfully wrote '{value}' to section '{section}', key '{key}'")
        except IOError as e:
            print(f"An I/O error occurred while writing to the file: {e}")

    def get_sessions(self) -> dict[str, dict[str, str]]:
        """
        Lists all available sessions in the config file.

        Returns:
            dict[str, dict[str, str]]: A dictionary where keys are session names and values are
            dictionaries of session properties.
        """
        sessions = []
        session_names = []
        config = configparser.ConfigParser()
        if self._config_path.is_file():
            config.read(self._config_path)
            for section in config.sections():
                if section.startswith('sso-session '):
                    session_names.append(section[len('sso-session '):])

        for name in session_names:
            section_name = 'sso-session ' + name
            session = {'name': name}
            for prop in ['sso_start_url', 'sso_region', 'sso_registration_scopes']:
                if not config.has_option(section_name, prop):
                    print(f"Warning: '{prop}' not found in section '{section_name}'")
                    continue
                session[prop] = config.get(section_name, prop, fallback=None)
            sessions.append(session)
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
        config = configparser.ConfigParser()
        if self._config_path.is_file():
            config.read(self._config_path)
            section_name = 'sso-session ' + name
            if config.has_section(section_name):
                config.remove_section(section_name)
                with open(self._config_path, 'w', encoding='utf-8') as configfile:
                    config.write(configfile)
                print(f"Successfully deleted session '{name}'")
            else:
                print(f"Session '{name}' not found in the config file")
        else:
            print(f"Error: AWS config file not found at {self._config_path}")

    def get_profiles(self) -> dict[str, dict[str, str]]:
        """
        Lists all available profiles in the config file.

        Returns:
            dict[str, dict[str, str]]: A dictionary where keys are profile names and values are
            dictionaries of profile properties.
        """
        profiles = {}
        profile_names = []
        config = configparser.ConfigParser()
        if self._config_path.is_file():
            config.read(self._config_path)
            for section in config.sections():
                if section.startswith('profile '):
                    profile_names.append(section[len('profile '):])
                elif section == 'default':
                    profile_names.append('default')

        for name in profile_names:
            section_name = 'profile ' + name if name != 'default' else 'default'
            profiles[name] = {}
            for prop in ['region', 'output', 'sso_session', 'sso_account_id', 'sso_role_name']:
                if not config.has_option(section_name, prop):
                    print(f"Warning: '{prop}' not found in section '{section_name}'")
                    continue
                profiles[name][prop] = config.get(section_name, prop, fallback=None)
        return profiles
