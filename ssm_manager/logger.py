"""
Custom Logger
"""
import logging
from flask import jsonify

class CustomLogger(logging.Logger):
    """
    Custom logger that extends the standard logging.Logger class to provide
    additional functionality for logging success and failure messages.
    """
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        # You can add a custom log level here if needed, e.g., for 'success'
        # logging.addLevelName(25, "SUCCESS")

    def success(self, msg, *args, **kwargs):
        """
        Logs a 'success' message with a custom format.
        """
        # You can customize the log level and format here
        self.log(logging.INFO, f"success: {msg}", *args, **kwargs)

        # Return a Flask response
        return jsonify({'status': 'success', 'message': msg}), 200

    def failed(self, msg, *args, **kwargs):
        """
        Logs a 'failed' message with a custom format and returns a Flask response.
        """
        # Log the error
        self.log(logging.ERROR, f"error: {msg}", *args, **kwargs)

        # Return a Flask response
        return jsonify({'status': 'error', 'message': msg}), 500
