"""
Client application helpers.
"""

import os
import sys
import threading
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from ssm_manager import logger, app_name
from ssm_manager.utils import open_browser
from ssm_manager.app import app

# pylint: disable=logging-fstring-interpolation


class ServerThread(threading.Thread):
    """
    Thread class for running the Flask server
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.daemon = True
        self.target = self.run
        self.debug = False
        self.use_reloader = False
        self.port = 5000

    def stop(self):
        """
        Stop the server
        """
        self._stop_event.set()

    def stopped(self):
        """
        Check if the server is stopped
        """
        return self._stop_event.is_set()

    def run(self):
        """
        Run the server
        """
        while not self.stopped():
            logger.info("Starting server...")
            try:
                app.run(
                    host="127.0.0.1",
                    port=self.port,
                    debug=self.debug,
                    use_reloader=self.use_reloader,
                )
            except FileNotFoundError:
                pass
            except Exception as e:  # pylint: disable=broad-except
                logger.error(f"Unexpected error: {str(e)}")
            finally:
                self.stop()


class TrayIcon:
    """
    System tray icon class
    """

    def __init__(self, icon_file, **kwargs):
        self.server = ServerThread()
        self.server.port = kwargs.get("server_port", 5000)
        self.server.daemon = True
        self.icon = None
        self.icon_file = self.get_resource_path(icon_file)

    @property
    def image(self):
        """
        Load the icon image
        """
        try:
            image = Image.open(self.icon_file)
        except FileNotFoundError:
            logger.warning("Icon file not found, generating fallback image")
            image = self.create_icon(32, 32, "black", "white")
        return image

    @property
    def menu(self):
        """
        Create the system tray menu
        """
        return Menu(
            MenuItem("Open", self.open_app, default=True),
            MenuItem("Exit", self.exit_app),
        )

    def get_resource_path(self, relative_path):
        """
        Get absolute path to resource, works for dev and for PyInstaller
        Args:
            relative_path (str): Relative path to the resource
        Returns:
            str: Absolute path to the resource
        """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            # pylint: disable=protected-access
            base_path = os.path.join(sys._MEIPASS, "ssm_manager")
        except AttributeError:
            base_path = os.path.dirname(os.path.realpath(__file__))

        return os.path.join(base_path, relative_path)

    def create_icon(self, width, height, color1, color2):
        """
        Generates a simple fallback image
        Args:
            width (int): Image width
            height (int): Image height
            color1 (str): Background color
            color2 (str): Foreground color
        Returns:
            Image: The generated image
        """
        image = Image.new("RGB", (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
        dc.rectangle((0, height // 2, width // 2, height), fill=color2)
        return image

    def exit_app(self, icon, item):
        """
        Exit the application
        """
        # pylint: disable=unused-argument
        self.server.stop()
        self.icon.stop()

    def open_app(self, *args):
        """
        Open the application in the default browser
        """
        # pylint: disable=unused-argument
        logger.info("Opening application...")
        open_browser(f"http://127.0.0.1:{self.server.port}/")

    def stop(self):
        """
        Stop the system tray icon
        """
        if self.icon:
            self.icon.stop()

    def run(self):
        """
        Run the system tray icon
        """
        try:
            self.server.start()
            self.icon = Icon(app_name, self.image, app_name, menu=self.menu)
            self.open_app(None, None)
            if not self.server.stopped():
                self.icon.run()
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Unexpected error: {str(e)}")
        finally:
            self.server.stop()
            self.icon.stop()
