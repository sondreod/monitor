import socket
from pathlib import Path


PORT = 8000
STORAGE_PATH = Path("~/.local/share/monitor/").expanduser()
HOSTNAME = socket.gethostname()
