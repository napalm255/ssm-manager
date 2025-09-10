"""
Initialization module for SSM Manager.
"""

# pylint: disable=invalid-name

import os
import sys
import platform
import logging
from ssm_manager.logger import CustomLogger
from ssm_manager.cache import Cache
from ssm_manager.deps import DependencyManager
from ssm_manager.manager import AWSManager
from ssm_manager.preferences import PreferencesHandler

# Define application name
app_name = "SSM Manager"
version = "0.0.0"

# Define server port
port = 5000

# Define home directory and app data directory
home_dir = os.path.expanduser("~")
data_dir = "ssm_manager"

# Define system and architecture
system = platform.system()
if system not in ["Linux", "Windows"]:
    print("Unsupported operating system")
    sys.exit(1)
arch = platform.machine()

# Define paths
version_file = os.path.join(os.path.dirname(__file__), "VERSION")
preferences_file = os.path.join(home_dir, f".{data_dir}", "preferences.json")
cache_dir = os.path.join(home_dir, f".{data_dir}", "cache")
lock_file = os.path.join(home_dir, f".{data_dir}", "ssm_manager.lock")
pid_file = os.path.join(home_dir, f".{data_dir}", "ssm_manager.pid")
temp_dir = os.path.join(home_dir, f".{data_dir}", "temp")
log_file = os.path.join(home_dir, f".{data_dir}", "ssm_manager.log")
hosts_file = os.path.join("/", "etc", "hosts")

if system == "Windows":
    preferences_file = os.path.join(
        home_dir, "AppData", "Local", data_dir, "preferences.json"
    )
    cache_dir = os.path.join(home_dir, "AppData", "Local", data_dir, "cache")
    lock_file = os.path.join(home_dir, "AppData", "Local", data_dir, "ssm_manager.lock")
    pid_file = os.path.join(home_dir, "AppData", "Local", data_dir, "ssm_manager.pid")
    temp_dir = os.path.join(home_dir, "AppData", "Local", data_dir, "temp")
    log_file = os.path.join(home_dir, "AppData", "Local", data_dir, "ssm_manager.log")
    hosts_file = os.path.join("C:\\", "Windows", "System32", "drivers", "etc", "hosts")

try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    # pylint: disable=protected-access
    base_path = os.path.join(sys._MEIPASS, "ssm_manager")
except AttributeError:
    base_path = os.path.dirname(os.path.realpath(__file__))

logo_file = os.path.join(base_path, "static/ssm-manager.png")


# Make sure directories exist
os.makedirs(os.path.dirname(preferences_file), exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)
os.makedirs(temp_dir, exist_ok=True)
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Configure detailed logging
logging.setLoggerClass(CustomLogger)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s:%(name)s - %(message)s",
    handlers=[logging.FileHandler(log_file, mode="w"), logging.StreamHandler()],
)

# Configure logger
logger = logging.getLogger("ssm_manager")

# Define version
with open(version_file, "r", encoding="utf-8") as vfile:
    version = vfile.read().strip()

# Define cache
cache = Cache(cache_dir=cache_dir)

# Define dependencies
deps = DependencyManager(system=system, arch=arch)

# Define AWS Manager
aws_manager = AWSManager()

# Setup preferences
preferences = PreferencesHandler(config_file=preferences_file)
