from fastapi import FastAPI

from monitor.api import v1
from monitor.collectors import run

app = FastAPI()
app.mount("/api/v1", v1)


run("monitor/inventory.toml", app=app)
