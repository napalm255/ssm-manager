"""
Main entry point for the application
"""

import os
import sys
import signal
import tkinter as tk
from tkinter import messagebox
from filelock import FileLock, Timeout
from ssm_manager import logger, app_name, port, lock_file, pid_file
from ssm_manager.client import ServerThread, TrayIcon
from ssm_manager.utils import open_browser

# pylint: disable=logging-fstring-interpolation

server = ServerThread()
tray = TrayIcon("static/favicon.ico", server_port=port)


def start(debug: bool, use_reloader: bool) -> None:
    """
    Start the server
    """
    server.port = port
    server.debug = debug
    server.use_reloader = use_reloader
    server.run()


def cleanup(*args) -> None:
    """
    Cleanup function to remove PID and lock files
    """
    # pylint: disable=unused-argument
    if os.path.exists(pid_file):
        os.remove(pid_file)
    if os.path.exists(lock_file):
        os.remove(lock_file)
    server.stop()
    tray.stop()
    logger.info("Exiting...")


def show_dialog(pid: int) -> None:
    """
    Displays a dialog box to manage the running application instance.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    message = "An instance of the application is already running."

    dialog = tk.Toplevel(root)
    dialog.title(f"{app_name}")
    dialog.geometry("600x100")
    dialog.resizable(False, False)

    label = tk.Label(dialog, text=message, wraplength=400)
    label.pack(pady=10)

    def open_app():
        open_browser(url="http://127.0.0.1:5000")
        dialog.destroy()
        sys.exit(0)

    def terminate_app():
        try:
            os.kill(pid, signal.SIGTERM)
            dialog.destroy()
            sys.exit(0)
        except Exception as e:  # pylint: disable=broad-except
            messagebox.showerror(app_name, f"Error terminating application: {e}")
            sys.exit(1)

    def cancel():
        dialog.destroy()
        sys.exit(0)

    # Create buttons
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=5)

    open_btn = tk.Button(button_frame, text="Open", command=open_app)
    open_btn.pack(side="left", padx=5)

    quit_btn = tk.Button(button_frame, text="Terminate", command=terminate_app)
    quit_btn.pack(side="left", padx=5)

    cancel_btn = tk.Button(button_frame, text="Cancel", command=cancel)
    cancel_btn.pack(side="left", padx=5)

    # Run the dialog
    root.mainloop()


def main() -> None:
    """
    Main function to start the application
    """
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    # Check if the app is being run by the reloader
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        logger.info("Reloader process detected. Starting server.")
        with open(pid_file, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        start(debug=True, use_reloader=True)
        return

    debug = False
    use_reloader = False
    api_only = False
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        api_only = True
        debug = True
        use_reloader = True

    lock = FileLock(lock_file, timeout=0)
    try:
        with lock:
            with open(pid_file, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            if not api_only:
                tray.run()
            else:
                start(debug=debug, use_reloader=use_reloader)
    except Timeout:
        with open(pid_file, "r", encoding="utf-8") as f:
            pid = f.read().strip()
        show_dialog(int(pid))
