# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import logging
import logging.handlers as lh
import queue
import subprocess as sp
import threading
from abc import ABC
from abc import abstractmethod


class ProcessHandler(threading.Thread, ABC):
    """
    This abstract class facilitates managing a process
    in the background and getting its stderr/stdout
    streams funnelled into a logging queue. Hence, a
    python program can run several such processes and
    manage their lifetimes with ease, while getting their
    output streams without lost or garbled data.
    """

    # Override these
    cmdline = []
    options = {}

    def __init__(self, log_handler: logging.Logger):
        super().__init__()
        self.name = type(self).__name__
        self.log = log_handler
        self._signal = threading.Event()
        self._signal.set()
        self._ignore_failure = False

    @abstractmethod
    def start_check(self) -> None:
        pass

    def run(self):
        self.log.debug(f"About to run: {self.cmdline} with opts: {self.options}")
        self.proc = sp.Popen(
            self.cmdline, text=True, stdout=sp.PIPE, stderr=sp.STDOUT, **self.options
        )
        rc = 1
        while self._signal.wait(0.02):
            rc = self.proc.poll()
            for line in self.proc.stdout.readlines(100):
                self.log.debug("IN> %s", line.rstrip())
            if rc is not None:
                self._signal.clear()
                if rc != 0:
                    self.log.warning("Unexpectedly died (rc=%d)", rc)
                break

    def set_ignore_failure(self, ignore: bool) -> None:
        self._ignore_failure = ignore

    def __enter__(self) -> "ProcessHandler":
        self.start()
        self.start_check()
        self.log.debug("%s: Yielding to 'with' body", self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.proc.terminate()
        self._signal.clear()
        self.join()

        rc = self.proc.poll()
        self.log.debug("finished process %snormally", "ab" if rc else "")
        if rc and not self._ignore_failure:
            raise ValueError


class SharedLogger:
    """
    This class implements the recommendations from Python's
    logging cookbook when having multiple threads pushing logs,
    in order to avoid getting the threads locked waiting for
    I/O:
    https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes
    """

    def __init__(self) -> None:
        self.queue = queue.Queue(-1)  # no limit on size

        queue_handler = lh.QueueHandler(self.queue)
        handler = logging.StreamHandler()
        self.listener = lh.QueueListener(self.queue, handler)

        self.log = logging.getLogger(__file__)
        self.log.propagate = False
        self.log.addHandler(queue_handler)
        formatter = logging.Formatter(
            "%(relativeCreated)6dms %(threadName)s [%(levelname)s]: %(message)s"
        )
        handler.setFormatter(formatter)

    def __enter__(self) -> logging.Logger:
        self.listener.start()
        return self.log

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.listener.stop()
