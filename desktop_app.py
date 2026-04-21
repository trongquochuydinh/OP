import socket
import threading
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import webview
from werkzeug.serving import make_server

from main import app


def _find_free_port(host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def _wait_for_server(url, timeout_seconds=15):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1):
                return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError(f"Flask server did not start in time at {url}")


class FlaskServerThread(threading.Thread):
    def __init__(self, flask_app, host, port):
        super().__init__(daemon=True)
        self._app = flask_app
        self._host = host
        self._port = port
        self._server = None
        self._ctx = None

    def run(self):
        self._server = make_server(self._host, self._port, self._app)
        self._ctx = self._app.app_context()
        self._ctx.push()
        self._server.serve_forever()

    def shutdown(self):
        if self._server is not None:
            self._server.shutdown()
        if self._ctx is not None:
            self._ctx.pop()


class DesktopBridge:
    def __init__(self):
        self._window = None

    def _open_dialog(self, file_types, allow_multiple=False):
        if self._window is None:
            return [] if allow_multiple else ""

        picked: Any = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=allow_multiple,
            directory=str(Path.cwd()),
            file_types=file_types,
        )
        if not picked:
            return [] if allow_multiple else ""

        if allow_multiple:
            if isinstance(picked, (list, tuple)):
                return [str(Path(path)) for path in picked]
            return [str(Path(picked))]

        if isinstance(picked, (list, tuple)):
            return str(Path(picked[0]))
        return str(Path(picked))

    def pick_source_files(self):
        return self._open_dialog(
            ("Data files (*.xlsx;*.yml;*.yaml)",),
            allow_multiple=True,
        )

    def pick_source_file(self):
        return self._open_dialog(
            ("Data files (*.xlsx;*.yml;*.yaml)",),
            allow_multiple=False,
        )

    def pick_docx_file(self):
        return self._open_dialog(
            ("DOCX files (*.docx)",),
            allow_multiple=False,
        )


def main():
    host = "127.0.0.1"
    port = _find_free_port(host)
    app_url = f"http://{host}:{port}"

    server_thread = FlaskServerThread(app, host, port)
    server_thread.start()
    _wait_for_server(app_url)

    bridge = DesktopBridge()
    window = webview.create_window(
        title="Data Plotter",
        url=app_url,
        js_api=bridge,
        min_size=(1100, 760),
        width=1440,
        height=920,
    )
    bridge._window = window

    try:
        webview.start()
    finally:
        server_thread.shutdown()
        server_thread.join(timeout=2)


if __name__ == "__main__":
    main()
