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
import toml
import re

from typing import Any


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


def replace_toml_placeholders(item: Any, defines: dict[str, str]) -> dict[str, Any]:
    """Recursively replaces any string or string within list and dicts with user defined values.

    Args:
        item (Any): A string, list or dict to act upon and replace any matching %...% pattern with defines.
        defines (dict[str, str]): A dictionary whose keys will be searched on item to be replaced with the associated
                                  values.

    Returns:
        dict[str, Any]: The parsed TOML dict where all substitutions have been performed on the user-defined keys.
    """

    if isinstance(item, str):
        for key, value in defines.items():
            placeholder = f"%{key}%"
            item = item.replace(placeholder, value)
        return item

    elif isinstance(item, list):
        return [replace_toml_placeholders(sub_item, defines) for sub_item in item]

    elif isinstance(item, dict):
        return {k: replace_toml_placeholders(v, defines) for k, v in item.items()}

    else:
        # Return the item unchanged if it's not a string, list, or dict
        return item


def replace_toml_regex(item: Any, substitute: bool = False) -> dict[str, Any]:
    """
    Recursively substitues all values corresponding to keys which include 'regex' with ``re.Patterns``.

    All generated patterns have a ``re.DOTALL`` flag set.

    Args:
         item (Any): A string, list or dict to act upon and replace any regex string with re.Pattern.
        substitute (bool, optional): Flag to allow substitution of value. Defaults to False.

    Returns:
        dict[str, Any]: The parsed TOML dict where all substitutions have been performed on the regex strings.
    """
    if isinstance(item, str) and substitute:
        return re.compile(f'{item}', re.DOTALL)

    elif isinstance(item, list):
        return [replace_toml_regex(elem, substitute) for elem in item]

    elif isinstance(item, dict):
        return {k: replace_toml_regex(v, True if "regex" in k else False) for k, v in item.items()}
    else:
        return item


def parse_a0_configuration(config_file: str) -> dict:
    """_summary_

    Args:
        config_file (str): _description_

    Returns:
        dict: _description_
    """

    try:
        config = toml.load(config_file)
    except toml.TomlDecodeError as e:
        print(f"Error decoding TOML: {e}")

    try:
        user_defines = config["user_defines"]
    except KeyError:
        pass

    if user_defines:
        config = replace_toml_placeholders(config, user_defines)

    # Change regex keys to re.Patterns
    config = replace_toml_regex(config)

    # TODO: Continue...


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
