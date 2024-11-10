import re
import subprocess

from monitor import make_inventory, Metric, collector, run


inventory = make_inventory(
    {
        "localhost": {},
    }
)


@collector(inventory)
def disk_usage(server):
    mount_point = "/"
    data = "\n".join(server.run_command(f"df -h {mount_point}"))

    yield Metric(
        "disk_usage",
        re.findall(r"(\d{1,3})%.*/$", data, flags=re.MULTILINE)[0],
        hostname=server.hostname,
    )


@collector(inventory)
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


@collector(inventory)
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


run()
