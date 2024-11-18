import json
import re
import sqlite3
import subprocess
from datetime import datetime
from multiprocessing import Process
from pathlib import Path
from time import sleep

import fabric
import uvicorn

from monitor.config import STORAGE_PATH

registry = {}
db = sqlite3.connect(STORAGE_PATH / "timeseries.db")


def run(inventory_file, app=None, port=None):
    """
    - serve the generated static files #set cache headers?
    - serve dashboard as json?
    - reducers should calculate min/max/avg/std fields?
    """

    def serve():
        uvicorn.run(app, port=port or 8000)

    if app:
        p = Process(target=serve)
        p.start()
    try:
        while True:
            i = parse_inventory_file(inventory_file)
            for server in i:
                for collector in server.collectors:
                    try:
                        [print(c.save()) for c in registry.get(collector)(server)]
                    except TypeError as e:
                        raise RuntimeError(
                            f"Could not find collector: {collector}.\nError: {e}"
                        )

            sleep(60)
    except KeyboardInterrupt:
        if app:
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


@collector()
def cpu_usage(server):
    if not server.local:
        usage = server.run_command(
            """awk '{u=$2+$4; t=$2+$4+$5; if (NR==1){u1=u; t1=t;} else print ($2+$4-u1) * 100 / (t-t1); }' <(grep 'cpu ' /proc/stat) <(sleep 1;grep 'cpu ' /proc/stat)"""
        )[0].strip()

        yield Metric("cpu_usage", usage, server.hostname)


@collector()
def cpu_load(server):

    load_1m, load5m, load15m, *_ = server.run_command("cat /proc/loadavg")[0].split(" ")
    num_of_cores = int(
        server.run_command("cat /proc/cpuinfo | grep 'cpu cores' | uniq")[0].split(":")[
            1
        ]
    )

    # yield Metric("cpu_cores", num_of_cores, server.hostname)
    yield Metric("cpu_load_m1", float(load_1m) / num_of_cores, server.hostname)


@collector()
def memory_usage(server):
    out = server.run_command("free -m")
    total, *_, available = re.findall(
        r"Mem:\s+(\d{1,9})\s+(\d{1,9})\s+(\d{1,9})\s+(\d{1,9})\s+(\d{1,9})\s+(\d{1,9})",
        "\n".join([x.strip() for x in out]),
        re.MULTILINE,
    )[0]

    # yield Metric("memory_total", total, server.hostname)
    yield Metric("memory_available", available, server.hostname)
    yield Metric(
        "memory_percent",
        int(round(100 - ((int(available) / int(total)) * 100), 0)),
        server.hostname,
    )


@collector()
def disk_usage(server):
    mount_point = "/"
    data = "\n".join(server.run_command(f"df -h {mount_point}"))

    yield Metric(
        "disk_usage",
        re.findall(r"(\d{1,3})%.*/$", data, flags=re.MULTILINE)[0],
        hostname=server.hostname,
    )


@collector(interval=60 * 60 * 24)
def days_left_to_tg(_):
    yield Metric("days_left_for_tg", (datetime(2025, 4, 14) - datetime.now()).days)


@collector()
def ping(server):
    if not server.local:
        result = subprocess.run(
            [f"ping -c 2 {server.hostname}"], shell=True, capture_output=True, text=True
        )
        minimum, average, maximum = re.findall(
            r"(\d{1,8}\.\d{1,6})(?=\/)", result.stdout.splitlines()[-1]
        )
        yield Metric(
            "ping",
            round(float(average)),
            server.hostname,
        )


@collector()
def uptime(server):
    out = server.run_command("uptime")

    days, hours = re.findall(
        r"up\s+(?:(\d{1,4}) days|(\d{1,2}:\d{1,2})),",
        "".join([x.strip() for x in out]),
    )[0]

    if not days:
        days = 0
    yield Metric(
        "uptime",
        days,
        server.hostname,
    )
