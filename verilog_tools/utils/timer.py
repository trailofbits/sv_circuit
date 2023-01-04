import time


class Timer(object):
    def __init__(self):
        self.start = None
        self.stop = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, _type, _value, _traceback):
        self.stop = time.time()

    @property
    def elapsed(self):
        if self.start is None:
            return 0
        if self.stop is None:
            return time.time() - self.start
        return self.stop - self.start

    def __str__(self) -> str:
        return str(self.elapsed)
