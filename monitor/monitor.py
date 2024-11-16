import subprocess
import functools
from pathlib import Path
from datetime import datetime
import http.server
import socketserver
from multiprocessing import Process
from time import sleep
import sqlite3

import fabric


PORT = 1234
STORAGE_PATH = Path("~/.local/share/monitor/").expanduser()

if not STORAGE_PATH.is_dir():
    STORAGE_PATH.mkdir(exist_ok=True, parents=True)

db = sqlite3.connect(STORAGE_PATH / "timeseries.db")
collectors = []


def run(start_server=True):
    """
    - serve the generated static files #set cache headers?
    - serve dashboard as json?
    - reducers should calculate min/max/avg/std fields?
    """

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=STORAGE_PATH, **kwargs)

    def serve():
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Listing on port {PORT}")
            httpd.serve_forever()

    if start_server:
        p = Process(target=serve)
        p.start()
    try:
        while True:
            [f() for f in collectors]
            sleep(60)
    except KeyboardInterrupt:
        if start_server:
            p.terminate()
            p.join()


def collector(servers=None, interval=15 * 60, active=True):
    """Decorator running the collect *func* on all servers and
    gathering the result."""
    # TODO: Implement interval

    def decorator_collector(func):

        @functools.wraps(func)
        def wrapper():
            result = []

            if active:
                if not servers:
                    result.extend(func())
                else:
                    timestamp = f"{datetime.now().isoformat(timespec="seconds")}+01:00"

                    for server in servers:
                        try:
                            for m in func(server):
                                m.timestamp = timestamp
                                result.append(m)
                        except Exception as e:
                            result.append(
                                Metric("monitor_error", str(e), server.hostname)
                            )

                [x.save() for x in result]

            return result

        wrapper.interval = interval
        collectors.append(wrapper)

        return wrapper

    return decorator_collector


class Server:
    def __init__(self, hostname, collectors=None, username="debian"):
        self.hostname = hostname
        self.username = username
        self.collectors = collectors or set()
        self.connection = None

        if self.hostname == "localhost":
            self.local = True
        else:
            self.local = False

        self.connect()

    def connect(self):
        if not self.local:
            self.connection = fabric.Connection(self.hostname, user=self.username)

    def run_command(self, command: str):
        if self.local:
            result = subprocess.run(
                [command], shell=True, capture_output=True, text=True
            )
            err = result.stderr
            if err:
                raise RuntimeError(" ".join(err))
            return result.stdout.splitlines()
        else:
            r = self.connection.run(command, hide=True)
            err = r.stderr
            if err:
                raise RuntimeError(" ".join(err))

            stdout = r.stdout.strip()
            return [stdout]

    def __hash__(self):
        return hash((self.hostname, self.username))

    def __repr__(self):
        return f'Server("{self.hostname}")'


class Metric:
    def __init__(self, name, value, hostname=None, timestamp=None):
        self.name = name
        self.value = value
        self.hostname = hostname
        self.timestamp = str(timestamp or int(datetime.now().timestamp()))

    def serialize(self):
        return f"{self.value},{self.hostname},{self.timestamp}\n"

    def __repr__(self):
        return f"Metric('{self.name}', {self.value}, '{self.hostname}')"

    def save(self):
        sql = """
        INSERT INTO metrics
            (timestamp, name, value, hostname)
        VALUES
            (?,?,?,?)"""
        db.execute(
            sql, (int(datetime.now().timestamp()), self.name, self.value, self.hostname)
        )
        db.commit()


def make_inventory(inventory: dict) -> list[Server]:
    return [Server(hostname, **config) for hostname, config in inventory.items()]
