#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import time
import logging
import sys

def setup_logger(name: str = "testcrush logger", log_file: str = "testcrush_debug.log") -> logging.Logger:
    """Set up a logger with stream and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Check if handlers already exist (to prevent adding them multiple times)
    if not logger.hasHandlers():
        # Stream handler (INFO level)
        log_stream = logging.StreamHandler(stream=sys.stdout)
        log_stream.setLevel(logging.INFO)
        log_stream.setFormatter(logging.Formatter('[%(levelname)s]: %(message)s'))

        # File handler (DEBUG level)
        log_file_handler = logging.FileHandler(filename=log_file, mode='w')
        log_file_handler.setLevel(logging.DEBUG)
        log_file_handler.setFormatter(logging.Formatter(
            '%(lineno)d:[%(levelname)s|%(module)s|%(funcName)s]: %(message)s'))

        logger.addHandler(log_stream)
        logger.addHandler(log_file_handler)

    return logger

log = setup_logger()

class Timer():
    """
    Context manager style timer. To be used as: ``with Timer():``
    """

    def __enter__(self):

        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):

        self.end = time.perf_counter()
        self.interval = self.end - self.start
        print(f"Execution time: {self.format_time(self.interval)}")

    def format_time(self, seconds):

        days, remainder = divmod(seconds, 86_400)  # 86400 seconds in a day
        hours, remainder = divmod(remainder, 3_600)  # 3600 seconds in an hour
        minutes, seconds = divmod(remainder, 60)  # 60 seconds in a minute
        return f"{int(days)}d {int(hours)}h {int(minutes)}m {seconds:.2f}s"


class Singleton(type):
    """
    Singleton design pattern. To be used as a metaclass: ``class A(metaclass = Singleton)``
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):

        if cls not in cls._instances:

            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance

        return cls._instances[cls]
