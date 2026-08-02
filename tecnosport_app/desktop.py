#!/usr/bin/env python3
"""
EnOrden - Desktop Windows
FastAPI + pywebview + PyInstaller
"""

import multiprocessing
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request

import uvicorn
import webview

APP_TITLE = "EnOrden"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

if sys.platform == "win32":
    if getattr(sys, "stdout", None) is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if getattr(sys, "stderr", None) is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server(port):
    try:
        from main import app

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
    except Exception:
        log_path = os.path.join(get_app_dir(), "enorden_server_error.log")
        with open(log_path, "w", encoding="utf-8") as error_log:
            error_log.write(traceback.format_exc())
        raise


def wait_for_server(url, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def main():
    os.chdir(get_app_dir())
    port = find_free_port()
    server_url = f"http://127.0.0.1:{port}"

    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    if not wait_for_server(server_url):
        raise RuntimeError("No se pudo iniciar el servidor local de EnOrden")

    webview.create_window(
        APP_TITLE,
        server_url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        resizable=True,
    )
    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        main()
    except Exception:
        log_path = os.path.join(get_app_dir(), "enorden_error.log")
        with open(log_path, "w", encoding="utf-8") as error_log:
            error_log.write(traceback.format_exc())
        raise
