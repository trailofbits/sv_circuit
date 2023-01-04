import subprocess
import typing
from dataclasses import dataclass
from io import StringIO

import psutil

from verilog_tools.utils.timer import Timer


@dataclass
class RunData:
    return_code: int
    run_duration: float
    peak_memory: typing.NamedTuple
    stdout: str


def run_and_profile(args, *, capture=False) -> RunData:
    with Timer() as elapsed:
        proc = subprocess.Popen(
            args, stdout=(subprocess.PIPE if capture else None), encoding="utf-8"
        )
        handle = psutil.Process(proc.pid)
        max_usage = handle.memory_info()

        captured_stdout = StringIO()

        finished = False
        while not finished:
            try:
                stdout, _stderr = proc.communicate(timeout=5)
                if capture:
                    captured_stdout.write(stdout)
                finished = True
            except subprocess.TimeoutExpired:
                current_usage = handle.memory_info()
                if current_usage.rss > max_usage.rss:
                    max_usage = current_usage

    print(cap := captured_stdout.getvalue())
    return RunData(
        return_code=proc.returncode,
        run_duration=elapsed.elapsed,
        peak_memory=max_usage,
        stdout=cap,
    )
