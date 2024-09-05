#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import os
import sys
import logging
import pathlib
import shutil
import zoix
import asm
import zipfile

from dataclasses import dataclass

######## TEMPORARY ########
log = logging.getLogger("testcrush logger")
log.setLevel(logging.DEBUG)
log_stream = logging.StreamHandler(stream = sys.stdout)
log_stream.setLevel(logging.INFO)
log_stream.setFormatter(logging.Formatter('[%(levelname)s]: %(message)s'))
log_file = logging.FileHandler(filename = "debug.log", mode = 'w')
log_file.setLevel(logging.DEBUG)
log_file.setFormatter(logging.Formatter('%(lineno)d:[%(levelname)s|%(module)s|%(funcName)s]: %(message)s'))
log.addHandler(log_stream)
log.addHandler(log_file)
###########################

def zip_archive(archive_name : str, *files) -> str:
    """Generates a .zip archive of arbitrary files.

    - Paremeters:
        - archive_name (str): The filename (stem) of the zip archive.

    - Returns:
        - str: The generated archive path string.
    """
    archive = pathlib.Path(archive_name)
    archive.mkdir(exist_ok = True)

    for file_ in files:
        shutil.copy(file_, archive)

    archive = archive.resolve()
    zip_filename = f"{archive.parent}/{archive.stem}.zip"

    with zipfile.ZipFile(zip_filename, 'w') as zipf:

        for foldername, _, filenames in os.walk(archive_name):

            for filename in filenames:

                file_path = f"{foldername}/{filename}"
                zipf.write(file_path, filename)

    return zip_filename

class A0():
    """Implements the A0 compaction algorithm of https://doi.org/10.1109/TC.2016.2643663"""

    def __init__(self, isa : str, *a0_asm_sources : str, **a0_settings) -> "A0":

        self.assembly_sources : list[asm.AssemblyHandler] = [
            asm.AssemblyHandler(isa, asm_file, chunksize = 1) # chunksize is always 1 for A0
            for asm_file in a0_asm_sources ]

        self.vc_zoix = zoix.ZoixInvoker()
        self.fsim_report = zoix.CSVFaultReport(
            fault_summary = a0_settings.get("fsim_fault_summary"),
            fault_report = a0_settings.get("fsim_fault_report"))

        self.zoix_compilation_args : list[str] = a0_settings.get("vcs_compilation_instructions", default = None)

        self.zoix_lsim_args : list[str] = a0_settings.get("logic_simulation_instructions")
        self.zoix_lsim_kwargs : dict[str, str] = a0_settings.get("logic_simulation_options")

        self.zoix_fcm_file : pathlib.Path = a0_settings.get("fcm_file")
        self.zoix_fcm_kwargs : dict[str, str] = a0_settings.get("fcm_options")

        self.zoix_fsim_args : list[str] = a0_settings.get("fault_simulation_instructions")
        self.zoix_fsim_kwargs : dict[str, str] = a0_settings.get("fault_simulation_options", default = None)

def main():
    """Sandbox/Testing Env"""

    zip_archive("test2", "test/1", "test/2", "test/3")


if __name__ == "__main__":
    main()
