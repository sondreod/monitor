import re
import subprocess
from datetime import datetime

from monitor import Metric, collector, run


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
def days_left_to_tg():
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


run("inventory.json", start_server=False)
