import time
from contextlib import contextmanager

@contextmanager
def track_time():
    start = time.time()
    yield lambda: time.time() - start

    