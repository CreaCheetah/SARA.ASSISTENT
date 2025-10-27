import logging, threading, datetime

class _RingBuffer(logging.Handler):
    def __init__(self, size: int = 500):
        super().__init__()
        self.size = size
        self.buf = []
        self.lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        line = {
            "ts": datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "msg": self.format(record),
        }
        with self.lock:
            self.buf.append(line)
            if len(self.buf) > self.size:
                self.buf = self.buf[-self.size:]

_handler: _RingBuffer | None = None

def setup_logging(size: int = 500):
    """Hang buffer aan uvicorn/error logger."""
    global _handler
    if _handler:
        return
    _handler = _RingBuffer(size=size)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    log = logging.getLogger("uvicorn.error")
    log.setLevel(logging.INFO)
    log.addHandler(_handler)

def get_events(n: int = 200):
    """Laatste n regels."""
    if not _handler:
        return []
    with _handler.lock:
        return list(_handler.buf[-n:])
