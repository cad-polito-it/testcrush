#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import time
import logging
import sys
import shutil
import subprocess
import pathlib
import zipfile
import os


def compile_assembly(*instructions, exit_on_error: bool = False) -> bool:
    """
    Executes a sequence of bash instructions to compile the `self.asm_file`. Uses subprocess for each instruction and
    optionally exits on error.

    Args:
        exit_on_error (bool): If an error is encountered during compilation and this is True, then the program
                              terminates. Otherwise it continues.
        *instructions (str): A sequence of bash commands required in order to (cross) compile the assembly files.

    Returns:
        bool: True if no message was written to ``stderr`` from any of the executed instructions (subprocesses).
        False otherwise.

    Raises:
        SystemExit: if ``stderr`` contains text and ``exit_on_error`` is True.
    """
    log.debug("Compiling assembly sources.")

    for cmd in instructions:

        log.debug(f"Executing instruction \"{cmd}\".")

        with subprocess.Popen(["/bin/bash", "-c", cmd],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True) as process:

            stdout, stderr = process.communicate()

            if stderr:

                log.debug(f"Error during execution of {cmd}\n\
                ---------[MESSAGE]---------\n\
                {'-'.join(stderr.splitlines())}\n\
                ---------------------------\n")

                if exit_on_error:

                    log.critical("Unrecoverable Error during compilation of assembly files. Exiting...")
                    exit(1)

                return False

            for line in stdout.splitlines():
                log.debug(f"{cmd}: {line.rstrip()}")

    return True


def zip_archive(archive_name: str, *files) -> str:
    """
    Generates a .zip archive of arbitrary files.

    Args:
        archive_name (str): The filename (stem) of the zip archive.

    Returns:
        str: The generated archive path string.
    """
    archive = pathlib.Path(archive_name)
    archive.mkdir(exist_ok=True)

    for file_ in files:
        shutil.copy(file_, archive)

    archive = archive.resolve()
    zip_filename = f"{archive.parent}/{archive.stem}.zip"

    with zipfile.ZipFile(zip_filename, 'w') as zipf:

        for foldername, _, filenames in os.walk(archive_name):

            for filename in filenames:

                file_path = f"{foldername}/{filename}"
                zipf.write(file_path, filename)

    shutil.rmtree(archive)
    return zip_filename


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
