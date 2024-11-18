import json
import subprocess
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
registry = {}


def run(inventory_file, start_server=True):
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
            i = parse_inventory_file(inventory_file)
            for server in i:
                for collector in server.collectors:
                    [print(c.save()) for c in registry.get(collector)(server)]

            break
    except KeyboardInterrupt:
        if start_server:
            p.terminate()
            p.join()


def collector(interval=15 * 60):
    """Use this functoin as a decorator to register a collector"""

    def wrapper(func):
        func.interval = interval
        registry[func.__name__] = func
        return func

    return wrapper


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
        return self


def parse_inventory_file(inventory_filepath: str) -> dict[str, Server]:
    with Path(inventory_filepath).open("r") as fd:
        inventory = json.load(fd)
        servers = []
        collection_groups = {}
        for k, v in inventory.items():
            if isinstance(v, list):
                collection_groups[k] = set(v)
            elif isinstance(v, dict):
                servers.append(Server(k, **v))
            else:
                raise RuntimeWarning(f"Can't parse inventory item: {k} {v}")

        for server in servers:
            new_collectors = set()
            for c in server.collectors:
                if c in collection_groups:

                    new_collectors = new_collectors | collection_groups[c]
                    server.collectors.remove(c)
            if new_collectors:
                server.collectors.extend(new_collectors)

        return servers
