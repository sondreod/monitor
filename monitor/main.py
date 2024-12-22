from fastapi import FastAPI

from monitor.api import v1

import re
import sqlite3
from functools import partial
from multiprocessing import Process
from time import sleep
import importlib

import uvicorn

from monitor.config import STORAGE_PATH
from monitor.registry import registry

db = sqlite3.connect(STORAGE_PATH / "timeseries.db")


loader = importlib.machinery.SourceFileLoader(
    "collectors", str(STORAGE_PATH / "collectors.py")
)
spec = importlib.util.spec_from_loader("collectors", loader)
collectors = importlib.util.module_from_spec(spec)
loader.exec_module(collectors)


def run(app=None, port=None):
    """
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
            for collector_name, collector_func in registry.items():
                try:
                    [print(c.save(db)) for c in collector_func()]
                except Exception as e:
                    raise RuntimeError(
                        f"Collector: {collector_name} failed with exception: {e}"
                    )

            sleep(60)
    except KeyboardInterrupt:
        if app:
            p.terminate()
            p.join()


def delute_older_metrics(db):
    cursor = db.cursor()
    cursor.execute("select * from metrics limit 10")
    while bulk := cursor.fetchmany():
        for record in bulk:
            print(record)
        print("kek")


if __name__ == "__main__":

    app = FastAPI()
    app.mount("/api/v1", v1)

    run(app=app)
