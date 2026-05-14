import time
from threading import Lock

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_time=30):
        self.lock = Lock()
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.last_failure_time = None
        self.recovery_time = recovery_time

    def is_open(self):
        if self.failure_count >= self.failure_threshold:
            if time.time() - self.last_failure_time > self.recovery_time:
                self.failure_count = 0
                return False
            return True
        return False

    def record_failure(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
        self.last_failure_time = time.time()

    def record_success(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
        self.failure_count = 0
    