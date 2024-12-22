import re
import subprocess
from datetime import datetime

from monitor.config import HOSTNAME
from monitor.models import Metric
from monitor.utils import run_command


def cpu_usage():
    usage = run_command(
        """awk '{u=$2+$4; t=$2+$4+$5;43221 if (NR==1){u1=u; t1=t;} else print ($2+$4-u1) * 100 / (t-t1); }' <(grep 'cpu ' /proc/stat) <(sleep 1;grep 'cpu ' /proc/stat)"""
    )[0].strip()

    yield Metric("cpu_usage", usage, HOSTNAME)


def cpu_load(server):

    load_1m, load5m, load15m, *_ = server.run_command("cat /proc/loadavg")[0].split(" ")
    num_of_cores = int(
        server.run_command("cat /proc/cpuinfo | grep 'cpu cores' | uniq")[0].split(":")[
            1
        ]
    )

    # yield Metric("cpu_cores", num_of_cores, server.hostname)
    yield Metric("cpu_load_m1", float(load_1m) / num_of_cores, server.hostname)


def memory_usage():
    out = run_command("free -m")
    total, *_, available = re.findall(
        r"Mem:\s+(\d{1,9})\s+(\d{1,9})\s+(\d{1,9})\s+(\d{1,9})\s+(\d{1,9})\s+(\d{1,9})",
        "\n".join([x.strip() for x in out]),
        re.MULTILINE,
    )[0]

    # yield Metric("memory_total", total, server.hostname)
    yield Metric("memory_available", available, HOSTNAME)
    yield Metric(
        "memory_percent",
        int(round(100 - ((int(available) / int(total)) * 100), 0)),
        HOSTNAME,
    )


def disk_usage():
    mount_point = "/"
    data = "\n".join(run_command(f"df -h {mount_point}"))

    yield Metric(
        "disk_usage",
        re.findall(r"(\d{1,3})%.*/$", data, flags=re.MULTILINE)[0],
        hostname=HOSTNAME,
    )


def ping(servers):
    for server in servers:
        result = subprocess.run(
            [f"ping -c 2 {server}"], shell=True, capture_output=True, text=True
        )
        minimum, average, maximum = re.findall(
            r"(\d{1,8}\.\d{1,6})(?=\/)", result.stdout.splitlines()[-1]
        )
        yield Metric(
            "ping",
            round(float(average)),
            server,
        )


def metric_check(hosts: tuple[str]):
    pass


def health_check(hosts: tuple[str]):
    pass


def uptime():
    out = run_command("uptime")

    try:
        days, hours = re.findall(
            r"up\s+(?:(\d{1,4}) days|(\d{1,2}:\d{1,2})),",
            "".join([x.strip() for x in out]),
        )[0]
    except IndexError:
        days = 0
    yield Metric("uptime", days, HOSTNAME)


def certificate_check(hosts: tuple[str]):
    from cryptography import x509
    import socket
    import ssl

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    for hostname in hosts:
        with socket.create_connection((hostname, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                data = ssock.getpeercert(True)
                pem_data = ssl.DER_cert_to_PEM_cert(data)
                cert_data = x509.load_pem_x509_certificate(str.encode(pem_data))
                yield Metric(
                    "certificate_expiry",
                    (
                        cert_data.not_valid_after_utc - datetime.today().astimezone()
                    ).days,
                    hostname,
                )
