from datetime import datetime
from functools import partial
from typing import Callable, Iterable, Mapping, Optional

from monitor.registry import registry


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

    def save(self, db):
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


def collector(interval=15 * 60, **kwargs):
    """Use this function as a decorator to register a collector"""

    def wrapper(func):
        func.interval = interval
        registry[func.__name__] = partial(func, **kwargs)
        return func

    return wrapper


def add_collector(func, **kwargs):
    """Use this to register a function you have imported.
    Otherwise use `collector` as decorator."""

    func.interval = kwargs.get("interval", 15 * 60)
    registry[func.__name__] = partial(func, **kwargs)


def add_collectors(collectors: Iterable[tuple[Callable, Optional[Mapping]]]):
    for element in collectors:
        kwargs = {}
        if isinstance(element, Callable):
            func = element
        else:
            func, kwargs = element
        add_collector(func, **kwargs)
