# src/ascii_art/server.py
import http.server
import os
import socketserver
import threading
import time
import webbrowser

from .ui import cool_print


class TextFileHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, file_to_serve=None, **kwargs):
        self.file_to_serve = file_to_serve
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # Silence server logs to keep terminal clean
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/myfile":
            try:
                with open(self.file_to_serve, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(404, f"File not found: {e}")
        else:
            self.send_error(404, "Not Found")


def start_server_and_open_browser(filepath):
    PORT = 8000

    def handler_factory(*args, **kwargs):
        return TextFileHandler(*args, file_to_serve=filepath, **kwargs)

    def run_server():
        # allow_reuse_address prevents "Address already in use" errors
        socketserver.TCPServer.allow_reuse_address = True
        # Check if port is available or catch error (simplified here)
        try:
            with socketserver.TCPServer(("", PORT), handler_factory) as httpd:
                httpd.serve_forever()
        except OSError as e:
            print(f"Warning: Could not start server on port {PORT}: {e}")

    # Start server thread as daemon so it dies when main program exits
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give server a moment to spin up
    time.sleep(1)

    url = f"http://localhost:{PORT}/myfile"

    # Print the link CLEARLY for WSL users
    cool_print(f"Server started. Access your art at: {url}\n")

    # Try to open browser, but don't crash if WSL Interop fails
    try:
        # Suppress stderr to hide "grep: ... WSLInterop" noise if possible
        # but Python's webbrowser module might print directly to stderr.
        webbrowser.open(url)
    except Exception:
        # If it fails, just ignore it since we printed the URL above
        pass
