import subprocess
import psutil
import logging
import time

logger = logging.getLogger(__name__)

def kill_process_tree(pid):
    """Kill a process and all its children"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        for child in children:
            try:
                child.terminate()
                child.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                child.kill() if child.is_running() else None
        
        parent.terminate()
        try:
            parent.wait(timeout=5)
        except psutil.TimeoutExpired:
            parent.kill()
            
        return True
    except psutil.NoSuchProcess:
        logger.warning(f"Process {pid} no longer exists")
        return False
    except Exception as e:
        logger.error(f"Error killing process tree: {str(e)}")
        return False

def check_aws_dependencies():
    """Check if required AWS CLI and plugins are installed"""
    try:
        # Check AWS CLI
        subprocess.check_output(
            ["aws", "--version"], 
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Check SSM plugin
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
    """Monitor active connections and remove dead ones"""
    dead_connections = []
    for conn in connections:
        if conn['process'].poll() is not None:
            dead_connections.append(conn)
    
    for conn in dead_connections:
        connections.remove(conn)
    
    return len(dead_connections)