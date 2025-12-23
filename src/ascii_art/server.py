# src/ascii_art/server.py
import http.server
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
        # Silence server logs
        pass

    def do_GET(self):
        # We serve the specific file at root or /myfile
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
            # Fallback
            self.send_error(404, "Not Found")


def start_server_and_open_browser(filepath):
    PORT = 8000

    # Factory to pass the specific filepath to the handler
    def handler_factory(*args, **kwargs):
        return TextFileHandler(*args, file_to_serve=filepath, **kwargs)

    def run_server():
        # allow_reuse_address prevents "Address already in use" errors on restart
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), handler_factory) as httpd:
            # We run loop logic outside, so we can't block forever if we want to exit cleanly
            # But simpler logic: run as daemon
            httpd.serve_forever()

    # Start server thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Open browser
    time.sleep(1)  # Wait for server to bind
    url = f"http://localhost:{PORT}/myfile"
    webbrowser.open(url)

    cool_print(f"Preview opened in browser at {url}\n")
