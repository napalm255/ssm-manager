"""
Application utility functions
"""
# pylint: disable=logging-fstring-interpolation
import logging
import subprocess
import psutil

logger = logging.getLogger(__name__)

def kill_process_tree(pid):
    """
    Kill a process and all its children
    Args:
        pid: Process ID to kill
    Returns: True if all processes were killed, False otherwise
    """
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)

        for child in children:
            try:
                child.terminate()
                child.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                logging.warning(f"Process {child.pid} no longer exists")
            finally:
                if child.is_running():
                    child.kill()
        parent.terminate()
        try:
            parent.wait(timeout=5)
        except psutil.TimeoutExpired:
            parent.kill()
        return True
    except psutil.NoSuchProcess:
        logger.warning(f"Process {pid} no longer exists")
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error killing process tree: {str(e)}")
    return False

def check_aws_dependencies():
    """
    Check if AWS CLI and SSM plugin are installed
    Returns: True if both dependencies are installed, False otherwise
    """
    try:
        subprocess.check_output(
            ["aws", "--version"],
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        subprocess.check_output(
            ["aws", "ssm", "start-session", "--version"],
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"AWS dependencies check failed: {str(e)}")
        return False

def monitor_connections(connections):
    """
    Monitor connections and remove dead connections
    Args:
        connections: List of active connections
    Returns: Number of dead connections
    """
    dead_connections = []
    for conn in connections:
        if conn['process'].poll() is not None:
            dead_connections.append(conn)
    for conn in dead_connections:
        connections.remove(conn)
    return len(dead_connections)
