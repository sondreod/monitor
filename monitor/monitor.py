import subprocess
import functools
from pathlib import Path
from datetime import datetime
import http.server
import socketserver
from multiprocessing import Process
from time import sleep

from paramiko import SSHClient

PORT = 1337
STORAGE_PATH = Path("~/.local/share/monitor/").expanduser()
if not STORAGE_PATH.is_dir():
    STORAGE_PATH.mkdir(exist_ok=True, parents=True)

collectors = []


def run():
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

    p = Process(target=serve)
    p.start()
    try:
        while True:
            [f() for f in collectors]
            sleep(60)
    except KeyboardInterrupt:
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
                    timestamp = (
                        str(datetime.now().isoformat(timespec="seconds")) + "+01:00"
                    )
                    for server in servers:
                        try:
                            server.create_session()
                            for m in func(server):
                                m.timestamp = timestamp
                                result.append(m)
                            server.close_session()
                        except Exception as e:
                            result.append(
                                Metric("monitor_error", str(e), server.hostname)
                            )
                            server.close_session()

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
        self.local = False
        self.ssh_client = None

        if self.hostname == "localhost":
            self.local = True

    def create_session(self):
        if not self.local:
            self.ssh_client = SSHClient()
            self.ssh_client.load_system_host_keys()

    def close_session(self, *args):
        if self.ssh_client:
            self.ssh_client.close()

    def __del__(self):
        if self.ssh_client:
            self.ssh_client.close()

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
            self.ssh_client.connect(hostname=self.hostname, username=self.username)
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            err = stderr.readlines()
            if err:
                raise RuntimeError(" ".join(err))
            return stdout.readlines()

    def __hash__(self):
        return hash((self.hostname, self.username))

    def __repr__(self):
        return f'Server("{self.hostname}")'


class Metric:
    def __init__(self, name, value, hostname=None, timestamp=None):
        self.name = name
        self.value = value
        self.hostname = hostname
        self.timestamp = (
            str(timestamp or datetime.now().isoformat(timespec="seconds")) + "+01:00"
        )

    def serialize(self):
        return f"{self.value},{self.hostname},{self.timestamp}\n"

    def save(self):

        with (STORAGE_PATH / f"{self.name}.csv").open("a") as fd:
            fd.write(self.serialize())


def make_inventory(inventory: dict) -> list[Server]:
    return [Server(hostname, **config) for hostname, config in inventory.items()]
