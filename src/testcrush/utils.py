#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import time
import re
import logging
import sys
import shutil
import subprocess
import pathlib
import zipfile
import os
import psutil
from typing import Literal

# # # # # # # # # # # # # # # # # # # # # #
#    __                   _               #
#   / /  ___   __ _  __ _(_)_ __   __ _   #
#  / /  / _ \ / _` |/ _` | | '_ \ / _` |  #
# / /__| (_) | (_| | (_| | | | | | (_| |  #
# \____/\___/ \__, |\__, |_|_| |_|\__, |  #
#             |___/ |___/         |___/   #
# # # # # # # # # # # # # # # # # # # # # #

trace_level_num = 5
logging.addLevelName(trace_level_num, "TRACE")


def trace(self, message, *args, **kws):
    if self.isEnabledFor(trace_level_num):
        self._log(trace_level_num, message, args, **kws, stacklevel=2)


logging.Logger.trace = trace


def setup_logger(stream_logging_level: int, log_file: str | None = None) -> None:
    """Set up a logger with stream and file handlers."""
    class IndentedFormatter(logging.Formatter):
        """Indents the record's body."""
        def format(self, record):

            original_message = super().format(record)

            indented_message = "\n>\t".join(original_message.splitlines())

            return indented_message

    _v_to_levels = {
        0: logging.INFO,
        1: logging.DEBUG,
        2: trace_level_num
    }

    logger = logging.getLogger(__name__)
    logger.setLevel(_v_to_levels[stream_logging_level])

    # Check if handlers already exist (to prevent adding them multiple times)
    if not logger.hasHandlers():

        log_stream = logging.StreamHandler(stream=sys.stdout)
        log_stream.setLevel(_v_to_levels[stream_logging_level])
        log_stream.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(log_stream)

        if log_file:
            log_file_handler = logging.FileHandler(filename=log_file, mode='w')
            log_file_handler.setLevel(_v_to_levels[stream_logging_level])
            log_file_handler.setFormatter(IndentedFormatter(
                '[%(levelname)s] @ %(module)s/%(funcName)s/line %(lineno)d\n%(message)s'))

            logger.addHandler(log_file_handler)


def get_logger() -> logging.Logger:
    """Return the pre-configured logger."""
    return logging.getLogger(__name__)


log = get_logger()


# # # # # # # # # # # #
#         _           #
#   /\/\ (_)___  ___  #
#  /    \| / __|/ __| #
# / /\/\ \ \__ \ (__  #
# \/    \/_|___/\___| #
# # # # # # # # # # # #

def to_snake_case(name: str) -> str:
    """
    Args:
        name (str): A camelCase-like string

    Returns:
        str: The ``name`` in snake_case format.
    """
    return ''.join(['_' + i.lower() if i.isupper() else i for i in name]).lstrip('_')


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

            if stderr and not re.search("warning", stderr, re.IGNORECASE):

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


def addr2line(elf_file: pathlib.Path, pc_address: str) -> tuple[str, int] | None:
    """
    Mimics the functionality of the addr2line binutil using pyelftools.
    Takes an ELF file and an address, and returns the corresponding
    file name and line number using the .debug_line section.

    Args:
        elf_file (pathlib.Path): The elf file.
        pc_address (str): The address of the program counter to look for within the elf in hexadecimal format as str.

    Returns:
        tuple: A file-line pair. The file (index-0) is the source which contains the line number that corresponds to the
        ``pc_address`` and the line (index-1) is the 1-based indexing of the line number within the source file.
    """

    from elftools.elf.elffile import ELFFile

    address = int(pc_address, 16)

    with open(elf_file, 'rb') as f:
        elf = ELFFile(f)

        if not elf.has_dwarf_info():
            log.debug(f"No DWARF info found in {elf_file}")
            return None

        dwarf_info = elf.get_dwarf_info()

        # Find the .debug_line section and retrieve line program information
        for CU in dwarf_info.iter_CUs():

            line_program = dwarf_info.line_program_for_CU(CU)

            if line_program:

                # Iterate over all entries in the line program
                for entry in line_program.get_entries():

                    state = entry.state

                    if state and state.address == address:

                        file_name = line_program['file_entry'][state.file - 1].name

                        return (file_name.decode('utf-8'), int(state.line))

    return (None, None)


def reap_process_tree(pid: int, timeout: float = 5.0) -> None:
    """Gracefully terminate and reap the process tree for a given PID.

    Args:
        pid (int): The process ID of the root process.
        timeout (float): Time in seconds to wait for processes to be reaped.
    """

    parent = psutil.Process(pid)
    children = parent.children(recursive=True)

    # First, try to gracefully terminate all processes in the tree
    log.info(f"Terminating process tree for PID {pid}...")
    for p in children:
        try:
            p.terminate()  # Sends SIGTERM
        except psutil.NoSuchProcess:
            continue  # Process might have exited already

    # Wait for the processes to terminate gracefully
    gone, alive = psutil.wait_procs(children, timeout=timeout)

    # For processes still alive after timeout, forcefully kill them
    if alive:
        log.info(f"Forcefully killing {len(alive)} processes...")
        for p in alive:
            try:
                p.kill()  # Sends SIGKILL
            except psutil.NoSuchProcess:
                continue

    # Finally, wait for all processes to be reaped
    gone, alive = psutil.wait_procs(alive, timeout=timeout)
    if not alive:
        log.info("All processes terminated and reaped.")
    else:
        log.info(f"Some processes could not be terminated: {[p.pid for p in alive]}")


# # # # # # # # # # # # # # # # # # #
#    ___ _                          #
#   / __\ | __ _ ___ ___  ___  ___  #
#  / /  | |/ _` / __/ __|/ _ \/ __| #
# / /___| | (_| \__ \__ \  __/\__ \ #
# \____/|_|\__,_|___/___/\___||___/ #
# # # # # # # # # # # # # # # # # # #

class Timer():
    """
    Timer class that can be used as a context manager or decorator to measure execution time.
    Can measure either wall-clock time or CPU process time.

    Usage as a context manager:

    .. code-block:: python

        with Timer(mode="wall"):
            # code block to time

    Usage as a decorator:

    .. code-block:: python

        @Timer(mode="cpu")
        def my_function(...):
            ...

    Args:
        mode (str): Timing mode. Either "wall" for wall-clock time (default)
            or "cpu" for CPU process time.
    """

    def __init__(self, mode: Literal["wall", "cpu"] = "wall"):
        self.mode = mode
        self.start: float
        self.end: float
        self.interval: float

    def __enter__(self):

        if self.mode == "wall":
            self.start = time.perf_counter()
        elif self.mode == "cpu":
            self.start = time.process_time()

        return self

    def __exit__(self, *args):

        if self.mode == "wall":
            self.end = time.perf_counter()
        elif self.mode == "cpu":
            self.end = time.process_time()

        self.interval = self.end - self.start
        print(f"Execution time: {self.format_time(self.interval)}")

    def __call__(self, func):

        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper

    def format_time(self, seconds):

        days, remainder = divmod(seconds, 86_400)  # 86400 seconds in a day
        hours, remainder = divmod(remainder, 3_600)  # 3600 seconds in an hour
        minutes, seconds = divmod(remainder, 60)  # 60 seconds in a minute

        return f"{int(days)}d {int(hours)}h {int(minutes)}m {seconds:.3f}s"


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
