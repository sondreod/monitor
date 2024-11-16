from fastapi import FastAPI

from monitor.api import v1


app = FastAPI()
app.mount("/api/v1", v1)
