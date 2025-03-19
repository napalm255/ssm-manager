"""
Application preferences handler
"""
# pylint: disable=logging-fstring-interpolation
import json
import logging
from pathlib import Path

class PreferencesHandler:
    """Handler for application preferences"""
    # pylint: disable=line-too-long

    DEFAULT_PREFERENCES = {
        "port_range": {
            "start": 60000,
            "end": 60100
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        }
    }

    def __init__(self, config_file="preferences.json"):
        """Initialize preferences handler"""
        self.config_file = Path(config_file)
        self.preferences = self.load_preferences()
        self.apply_preferences()

    def load_preferences(self):
        """Load preferences from file or create default if not exists"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_prefs = json.load(f)
                    return {**self.DEFAULT_PREFERENCES, **loaded_prefs}
            else:
                self.save_preferences(self.DEFAULT_PREFERENCES)
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f"Error loading preferences: {str(e)}")
        return self.DEFAULT_PREFERENCES

    def save_preferences(self, preferences):
        """Save preferences to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, indent=4)
            self.preferences = preferences
            self.apply_preferences()
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f"Error saving preferences: {str(e)}")
        return False

    def apply_preferences(self):
        """Apply current preferences to application"""
        try:
            log_level = self.preferences['logging']['level']
            numeric_level = getattr(logging, log_level.upper())
            logging.getLogger().setLevel(numeric_level)

            log_format = self.preferences['logging']['format']
            for handler in logging.getLogger().handlers:
                handler.setFormatter(logging.Formatter(log_format))

            logging.info("Applied preferences successfully")
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f"Error applying preferences: {str(e)}")

    def get_port_range(self):
        """Get port range for free port finder"""
        port_range = self.preferences.get('port_range', self.DEFAULT_PREFERENCES['port_range'])
        return port_range['start'], port_range['end']

    def update_preferences(self, new_preferences):
        """Update preferences with new values"""
        try:
            updated_prefs = {**self.preferences, **new_preferences}
            if self.save_preferences(updated_prefs):
                logging.info("Preferences updated successfully")
                return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error(f"Error updating preferences: {str(e)}")
        return False
