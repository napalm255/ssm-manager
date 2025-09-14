"""
Application preferences handler
"""

# pylint: disable=logging-fstring-interpolation
import logging
import json
from pathlib import Path
import keyring

logger = logging.getLogger(__name__)


class PreferencesHandler:
    """Handler for application preferences"""

    # pylint: disable=line-too-long

    DEFAULT_PREFERENCES = {
        "port_range": {"start": 60000, "end": 65535},
        "logging": {"level": "INFO"},
        "regions": [],
        "instances": [],
        "credentials": [],
        "port_forwarding": {"mode": "local", "remote_port": 1433},
    }

    def __init__(self, config_file="preferences.json"):
        """Initialize preferences handler"""
        self.config_file = Path(config_file)
        self.preferences = None
        self.load_preferences()
        self.apply_preferences()

    def load_preferences(self):
        """Load preferences from file or create default if not exists"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_prefs = json.load(f)
                    self.preferences = {**self.DEFAULT_PREFERENCES, **loaded_prefs}
            else:
                self.save_preferences(self.DEFAULT_PREFERENCES)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error loading preferences: {str(e)}")

    def reload_preferences(self):
        """Reload preferences from file"""
        self.load_preferences()
        self.apply_preferences()

    def update_instance_preferences(self, instance_name, new_preferences):
        """Update preferences for a specific instance"""
        try:
            prefs = self.preferences.copy()
            updated = False
            for pref in prefs.get("instances", []):
                if pref.get("name") == instance_name:
                    pref.update(new_preferences)
                    updated = True
                    break
            if not updated:
                new_instance = {"name": instance_name, **new_preferences}
                prefs["instances"].append(new_instance)
            prefs["instances"] = new_preferences.get("instances", prefs["instances"])
            if self.save_preferences(prefs):
                logger.info("Instance preferences updated successfully")
                return True
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error updating instance preferences: {str(e)}")
        return False

    def update_preferences(self, new_preferences):
        """Update preferences with new values"""
        try:
            prefs = self.preferences.copy()
            prefs["port_range"] = new_preferences.get("port_range", prefs["port_range"])
            prefs["logging"] = new_preferences.get("logging", prefs["logging"])
            prefs["regions"] = new_preferences.get("regions", prefs["regions"])
            prefs["instances"] = new_preferences.get("instances", prefs["instances"])
            prefs["port_forwarding"] = new_preferences.get(
                "port_forwarding", prefs["port_forwarding"]
            )
            prefs["credentials"] = [
                {"username": cred.get("username")}
                for cred in new_preferences.get("credentials", prefs["credentials"])
                if cred.get("username")
            ]
            usernames = [cred.get("username") for cred in prefs["credentials"]]
            credentials_to_delete = [
                cred.get("username")
                for cred in new_preferences.get("credentials_to_delete", [])
            ]

            for cred in self.preferences.get("credentials", []):
                if cred.get("username") not in usernames:
                    credentials_to_delete.append(cred.get("username"))

            if not self.delete_credentials(credentials_to_delete):
                logger.warning("Failed to delete one or more credentials")
                return False
            print(f"Deleting credentials for: {credentials_to_delete}")
            print(f"Saving credentials for: {prefs['credentials']}")
            if not self.save_credentials(
                new_preferences.get("credentials", prefs["credentials"])
            ):
                logger.warning("Failed to update credentials")
                return False
            if self.save_preferences(prefs):
                logger.info("Preferences updated successfully")
                return True
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error updating preferences: {str(e)}")
        return False

    def delete_credentials(self, usernames):
        """Delete credentials for given usernames"""
        if not isinstance(usernames, list):
            usernames = [usernames]
        for username in usernames:
            if not username:
                logger.debug("Skipping empty username")
                continue
            try:
                keyring.delete_password("ssm_manager", username)
                logger.info(f"Deleted credentials for {username}")
            except keyring.errors.PasswordDeleteError as e:
                logger.error(f"Error deleting credentials for {username}: {str(e)}")
        return True

    def save_credentials(self, credentials):
        """Save credentials to keyring"""
        for cred in credentials:
            username = cred.get("username", "")
            if username == "":
                logger.debug("Skipping credential with no username")
                continue
            password = cred.get("password", "")
            if password == "":
                logger.debug("Skipping credential with no password")
                continue
            logger.debug(f"Saving credentials for {username}")
            try:
                keyring.delete_password("ssm_manager", username)
            except keyring.errors.PasswordDeleteError:
                logger.debug(f"No existing credentials for {username} to delete")
            try:
                keyring.set_password("ssm_manager", username, password)
            except keyring.errors.PasswordSetError as e:
                logger.error(f"Error setting password for {username}: {str(e)}")
                return False
        return True

    def save_preferences(self, preferences):
        """Save preferences to file"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(preferences, f, indent=2)
            self.reload_preferences()
            return True
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error saving preferences: {str(e)}")
        return False

    def apply_preferences(self):
        """Apply current preferences to application"""
        try:
            log_level = self.preferences["logging"]["level"]
            numeric_level = getattr(logging, log_level.upper())

            # Set specific log levels for different components
            logging.getLogger("boto3").setLevel(logging.WARNING)
            logging.getLogger("botocore").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("werkzeug").setLevel(numeric_level)
            logging.getLogger("ssm_manager").setLevel(numeric_level)
            logging.getLogger("ssm_manager.preferences").setLevel(numeric_level)
            logging.getLogger("ssm_manager.manager").setLevel(numeric_level)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Error applying preferences: {str(e)}")

    def get_used_ports(self):
        """Get list of all used local ports"""
        used_ports = []
        for instance in self.preferences.get("instances", []):
            for port in instance.get("ports", []):
                used_ports.append(int(port.get("local_port")))
        return used_ports

    def get_instance_properties(self, name, remote_port: int, remote_host=None):
        """Get properties for specific instance"""
        for instance in self.preferences.get("instances", []):
            if instance.get("name") != name:
                continue
            for port in instance.get("ports", []):
                if int(port.get("remote_port")) != remote_port:
                    continue
                if remote_host and port.get("remote_host") != remote_host:
                    continue
                return int(port.get("local_port"))
        return None

    def get_port_range(self, name, remote_port: int, remote_host=None):
        """Get port range for free port finder"""
        local_port = self.get_instance_properties(name, remote_port, remote_host)
        if local_port:
            message = f"{remote_host} proxying via {name}" if remote_host else f"{name}"
            logging.info(f"Using preferred local port {str(local_port)} for {message}")
            return local_port, local_port
        port_range = self.preferences.get(
            "port_range", self.DEFAULT_PREFERENCES["port_range"]
        )
        return port_range["start"], port_range["end"]

    def get_regions(self):
        """Get regions for AWS services"""
        regions = self.preferences.get("regions", self.DEFAULT_PREFERENCES["regions"])
        return regions
