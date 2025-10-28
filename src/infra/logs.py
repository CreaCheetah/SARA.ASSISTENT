# src/infra/logs.py
import os, json, time, logging
from collections import deque

_LOG_PATH = "/tmp/events.log"

class JsonLineHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            obj = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "msg": record.getMessage(),
            }
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        except Exception:
            pass  # nooit crashen op logging

def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(JsonLineHandler())
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

def get_events(n: int = 200):
    if not os.path.exists(_LOG_PATH):
        return []
    last = deque(maxlen=n)
    with open(_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            last.append(line)
    out = []
    for line in last:
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"ts": "", "level": "INFO", "msg": line.strip()})
    return out
