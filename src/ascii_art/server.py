# src/ascii_art/server.py
import http.server
import shutil
import socketserver
import subprocess
import threading
import time
import webbrowser

from .ui import cool_print

# --- GLOBAL STATE ---
SERVER_STATE = {"current_file": None, "is_running": False}


class DynamicFileHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence server logs
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/myfile":
            filepath = SERVER_STATE["current_file"]

            if not filepath:
                self.send_error(404, "No file currently loaded.")
                return

            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(404, f"File not found: {e}")
        else:
            self.send_error(404, "Not Found")


def open_browser_silently(url):
    """
    Opens the browser using PowerShell on WSL/Windows to avoid
    'grep: WSLInterop' stderr noise from Python's webbrowser module.
    """
    # 1. Try Windows/WSL native method (Silent)
    if shutil.which("powershell.exe"):
        try:
            subprocess.run(
                ["powershell.exe", "-c", "start", f"'{url}'"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            pass

    # 2. Fallback to standard Python way (Linux/Mac)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def start_server_and_open_browser(filepath):
    PORT = 8000

    SERVER_STATE["current_file"] = filepath
    url = f"http://localhost:{PORT}/myfile"

    # If server is already running, just open browser
    if SERVER_STATE["is_running"]:
        cool_print(f"Server already running. Updating content...\n")
        cool_print(f"Opening browser at: {url}\n")
        open_browser_silently(url)
        return

    # Start new server
    def run_server():
        socketserver.TCPServer.allow_reuse_address = True
        try:
            with socketserver.TCPServer(("", PORT), DynamicFileHandler) as httpd:
                SERVER_STATE["is_running"] = True
                httpd.serve_forever()
        except OSError as e:
            print(f"Warning: Could not start server: {e}")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time.sleep(1)

    cool_print(f"Server started. Access your art at: {url}\n")
    open_browser_silently(url)
