from fastapi import FastAPI

from monitor.api import v1
from monitor.collectors import run
from monitor.config import STORAGE_PATH

app = FastAPI()
app.mount("/api/v1", v1)


if not STORAGE_PATH.is_dir():
    STORAGE_PATH.mkdir(exist_ok=True, parents=True)


run("monitor/inventory.json", app=app)
