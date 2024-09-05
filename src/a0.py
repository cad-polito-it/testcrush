#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import os
import sys
import logging
import pathlib
import shutil
import subprocess
import re
import random
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

def compile_assembly(exit_on_error : bool = False, *instructions) -> bool:
    """Executes a sequence of bash instructions to compile the `self.asm_file`.
    Uses subprocess for each instruction and optionally exits on error.

    - Parameters:
        - exit_on_error (bool): If an error is encountered during
        compilation and this is True, then the program terminates.
        Otherwise it continues.
        - *instructions (str): A sequence of bash commands
        required in order to (cross) compile the assembly files.

    - Returns:
        - bool: True if no message was written to `stderr` from any
        of the executed instructions (subprocesses). False otherwise."""

    for cmd in instructions:

        log.debug(f"Executing instruction '{cmd}'.")

        with subprocess.Popen(
            ["/bin/bash", "-c", cmd],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            text = True) as process:

            stdout, stderr = process.communicate()

            if stderr:
                log.debug(f"Error during execution of {cmd}\n\
                ---------[MESSAGE]---------\n\
                {'-'.join(stderr.splitlines())}\n\
                ---------------------------\n")

                if exit_on_error:

                    log.fatal(f"Unrecoverable Error during compilation of assembly files. Exiting...")
                    exit(1)

                return False

            for line in stdout.splitlines():
                log.debug(f"{cmd}: {line.rstrip()}")

    return True

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

    shutil.rmtree(archive)
    return zip_filename

def coverage(coverage_formula : str) -> float:
    # TODO: Compute coverage (eval trick), or add it to zoix.CSVFaultReport?
    ...
class A0():
    """Implements the A0 compaction algorithm of https://doi.org/10.1109/TC.2016.2643663"""

    def __init__(self, isa : str, *a0_asm_sources : str, **a0_settings) -> "A0":

        log.debug(f"Generating AssemblyHandlers for {a0_asm_sources}")
        self.assembly_sources : list[asm.AssemblyHandler] = [
            asm.AssemblyHandler(isa, pathlib.Path(asm_file), chunksize = 1) # chunksize is always 1 for A0
            for asm_file in a0_asm_sources ]

        self.assembly_compilation_instructions = a0_settings.get("assembly_compilation_instructions")

        self.fsim_report = zoix.CSVFaultReport(
            fault_summary = pathlib.Path(a0_settings.get("fsim_fault_summary")),
            fault_report = pathlib.Path(a0_settings.get("fsim_fault_report")))
        log.debug(f"Fault reports set to {self.fsim_report=}")

        self.zoix_compilation_args : list[str] = a0_settings.get("vcs_compilation_instructions")
        log.debug(f"VCS Compilation instructions for HDL sources set to {self.zoix_compilation_args}")

        self.zoix_lsim_args : list[str] = a0_settings.get("logic_simulation_instructions")
        self.zoix_lsim_kwargs : dict[str, float | re.Pattern | int | list] = \
            { k : eval(v) for k, v in  a0_settings.get("logic_simulation_options").items() }

        self.zoix_fcm_file : pathlib.Path = pathlib.Path(a0_settings.get("fcm_file"))
        self.zoix_fcm_kwargs : dict[str, str] = a0_settings.get("fcm_options")

        self.zoix_fsim_args : list[str] = a0_settings.get("fault_simulation_instructions")
        self.zoix_fsim_kwargs : dict[str, float] = \
            { k : eval(v) for k, v in  a0_settings.get("fault_simulation_options").items() }

    def run(self) -> None:

        vc_zoix = zoix.ZoixInvoker()
        vc_zoix.create_fcm_script(self.zoix_fcm_file, **self.zoix_fcm_kwargs)

        # Keep a backup of all sources since
        # they will be modified in-place.
        zip_archive("../backup", *[ asm.get_asm_source() for asm in self.assembly_sources])

        all_instructions : list[asm.Codeline] = \
            [ (asm_id, codeline) for asm_id, asm in enumerate(self.assembly_sources, start = 1) for codeline in asm.get_code() ]

        for i in range(100):
            random.shuffle(all_instructions)

        # Step 0: Initial fault simulation for  the
        #         computation of the fault coverage
        compile_assembly(*self.assembly_compilation_instructions)

        if self.zoix_compilation_args:
            vc_zoix.compile_sources(*self.zoix_compilation_args)

        # Continue ... TODO

        return True

def main():
    """Sandbox/Testing Env"""

    a0_sources = [ "../sandbox/sbst_01/src/tests/test1.S", "../sandbox/sbst_02/src/tests/test1_short_div.S" ]
    a0_settings = {
        "assembly_compilation_instructions" : ["make all"],
        "fsim_fault_summary" : "mock_fault_summary",
        "fsim_fault_report"  : "mock_fault_report",
        "vcs_compilation_instructions" : ["make all"],
        "logic_simulation_instructions" : ["make vcs/lsim/gate/shell"],
        "logic_simulation_options" : {
            "timeout" : "120.0",
            "success_regexp" : 're.compile(r"\$finish[^0-9]+([0-9]+)[m|u|n|p]s", re.DOTALL)',
            "tat_capture_group" : "1"
        },
        "fcm_file" : "fcm.tcl",
        "fcm_options" : {
            "set_config" : "-global_max_jobs 64",
            "create_testcases" : '-name {"test1"} -exec ${::env(VCS_WORK_DIR)}/simv -args "./simv +firmware=${::env(FIRMWARE)}" -fsim_args "-fsim=fault+dictionary"',
            "fsim" : "-verbose",
            "report" : "-campaign cv32e40p -report fsim_out.rpt -overwrite",
            "report" : "-campaign cv32e40p -report fsim_out_hier.rpt -overwrite -hierarchical 3"
        },
        "fault_simulation_instructions" : ["make vcs/fsim/gate/shell"],
        "fault_simulation_options" : {
            "timeout" : "None",
        }
    }
    isa = asm.ISA(pathlib.Path("../langs/riscv.isa"))

    A = A0(isa, *a0_sources, **a0_settings)

    A.run()

if __name__ == "__main__":
    main()
