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


def center_window(window: tk.Toplevel) -> None:
    """
    Center the window on the screen
    """
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")


def show_window(pid: int) -> None:
    """
    Displays a dialog box to manage the running application instance.
    """
    root = tk.Tk()
    root.title(f"{app_name}")
    root.geometry("600x100")
    root.protocol("WM_DELETE_WINDOW", lambda: exit_window(root))

    center_window(root)

    message = f"{app_name} is already running."

    label = tk.Label(root, text=message, wraplength=400)
    label.pack(pady=10)

    def open_app():
        open_browser(url="http://127.0.0.1:5000")
        exit_window(root)

    def exit_app():
        try:
            os.kill(pid, signal.SIGTERM)
            exit_window(root)
        except Exception as e:  # pylint: disable=broad-except
            messagebox.showerror(app_name, f"Error terminating application: {e}")
            sys.exit(1)

    # Create buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)

    open_btn = tk.Button(button_frame, text="Open", command=open_app)
    open_btn.pack(side="left", padx=5)

    quit_btn = tk.Button(button_frame, text="Terminate", command=exit_app)
    quit_btn.pack(side="left", padx=5)

    cancel_btn = tk.Button(
        button_frame, text="Cancel", command=lambda: exit_window(root)
    )
    cancel_btn.pack(side="left", padx=5)

    # Run the dialog
    root.mainloop()
    exit_window(root)


def exit_window(window: tk.Toplevel) -> None:
    """
    Exit the dialog and application
    """
    window.destroy()
    sys.exit(0)


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

    api_only = False
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        api_only = True

    lock = FileLock(lock_file, timeout=0)
    try:
        with lock:
            with open(pid_file, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
            if not api_only:
                tray.run()
            else:
                start(debug=api_only, use_reloader=api_only)
    except Timeout:
        with open(pid_file, "r", encoding="utf-8") as f:
            pid = f.read().strip()
        show_window(int(pid))
