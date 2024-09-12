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

def compile_assembly(*instructions, exit_on_error : bool = False) -> bool:
    """
    Executes a sequence of bash instructions to compile the `self.asm_file`.
    Uses subprocess for each instruction and optionally exits on error.

    Args:
        exit_on_error (bool): If an error is encountered during
                              compilation and this is True, then the
                              program terminates. Otherwise it continues.
        *instructions (str): A sequence of bash commands required in order to
                             (cross) compile the assembly files.

    Returns:
        bool: True if no message was written to ``stderr`` from any
        of the executed instructions (subprocesses). False otherwise.

    Raises:
        SystemExit: if ``stderr`` contains text and ``exit_on_error`` is True.
    """
    log.debug("Compiling assembly sources.")

    for cmd in instructions:

        log.debug(f"Executing instruction \"{cmd}\".")

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

                    log.critical("Unrecoverable Error during compilation of \
assembly files. Exiting...")
                    exit(1)

                return False

            for line in stdout.splitlines():
                log.debug(f"{cmd}: {line.rstrip()}")

    return True

def zip_archive(archive_name: str, *files) -> str:
    """
    Generates a .zip archive of arbitrary files.

    Paremeters:
        archive_name (str): The filename (stem) of the zip archive.

    Returns:
        str: The generated archive path string.
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


class A0():
    """Implements the A0 compaction algorithm of
    https://doi.org/10.1109/TC.2016.2643663"""

    def __init__(self, isa: str, *a0_asm_sources: str, **a0_settings) -> "A0":

        log.debug(f"Generating AssemblyHandlers for {a0_asm_sources}")
        self.assembly_sources: list[asm.AssemblyHandler] = [
            asm.AssemblyHandler(isa, pathlib.Path(asm_file), chunksize = 1) # chunksize is always 1 for A0
            for asm_file in a0_asm_sources]

        self.assembly_compilation_instructions = \
            a0_settings.get("assembly_compilation_instructions")
        self.fsim_report = zoix.CSVFaultReport(
            fault_summary = pathlib.Path(a0_settings.get("fsim_fault_summary")),
            fault_report = pathlib.Path(a0_settings.get("fsim_fault_report")))
        self.sff_config = a0_settings.get("sff_config")
        self.coverage_formula = a0_settings.get("coverage_formula")
        log.debug(f"Fault reports set to {self.fsim_report=}")

        self.zoix_compilation_args : list[str] = a0_settings.get("vcs_compilation_instructions")
        log.debug(f"VCS Compilation instructions for HDL sources set to {self.zoix_compilation_args}")

        self.zoix_lsim_args : list[str] = a0_settings.get("logic_simulation_instructions")
        self.zoix_lsim_kwargs : dict[str, float | re.Pattern | int | list] = \
            {k : eval(v) for k, v in
             a0_settings.get("logic_simulation_options").items()}

        self.zoix_fcm_file : pathlib.Path = pathlib.Path(a0_settings.get("fcm_file"))
        self.zoix_fcm_kwargs : dict[str, str] = a0_settings.get("fcm_options")

        self.zoix_fsim_args : list[str] = a0_settings.get("fault_simulation_instructions")
        self.zoix_fsim_kwargs : dict[str, float] = \
            {k : eval(v) for k, v in
             a0_settings.get("fault_simulation_options").items()}

        self.vc_zoix = zoix.ZoixInvoker()

    @staticmethod
    def evaluate(previous_result: tuple[int, float],
                 new_result: tuple[int, float]) -> bool:
        """
        Evaluates the new results with respect to the previous ones.

        Specifically, if new tat <= old tat and
        if new coverage >= old coverage.

        Args:
            previous_result (tuple[int, float]): the old tat value (int) and
                                                 coverage (float) values.
            new_result (tuple[int, float]): the new tat value (int) and
                                            coverage values.

        Returns:
            bool: ``True`` if new tat <= old tat and new coverage >= old
            coverage. ``False`` otherwise
        """

        old_tat, old_coverage = previous_result
        new_tat, new_coverage = new_result

        return (new_tat <= old_tat) and (new_coverage >= old_coverage)

    def get_coverage(self) -> float:
        ...

    def pre_run(self) -> tuple[int, float]:
        """
        Extracts the initial test application time and coverage of the STL.

        The test application time is extracted by a logic simulation of the STL
        whereas the coverage is computed by performing a fault simulation.

        Returns:
            tuple[int, float]: The test application time (index 0) and the
            coverage of the STL (index 1)
        Raises:
            SystemExit: If HDL sources cannot be compiled (if specified) or
                        if logic simulation cannot be performed.
            TimeoutError: if logic or fault simulation timed out.
        """

        vc_zoix = self.vc_zoix
        fault_report = self.fsim_report

        test_application_time = list()

        compile_assembly(*self.assembly_compilation_instructions)

        if self.zoix_compilation_args:

            comp = vc_zoix.compile_sources(*self.zoix_compilation_args)

            if comp == zoix.Compilation.ERROR:

                log.critical("Unable to compile HDL sources!")
                exit(1)

        try:

            lsim = vc_zoix.logic_simulate(*self.zoix_lsim_args,
                                          **self.zoix_lsim_kwargs,
                                          tat_value = test_application_time)

        except zoix.LogicSimulationException:

            log.critical("Unable to perform logic simulation for tat \
computation")
            exit(1)

        if lsim == zoix.LogicSimulation.TIMEOUT:

            raise TimeoutError("Logic simulation timed out")


        fsim = vc_zoix.fault_simulate(*self.zoix_fsim_args,
                                      **self.zoix_fsim_kwargs)

        if fsim == zoix.FaultSimulation.TIMEOUT:

            raise TimeoutError("Fault simulation timed out")

        fault_list = fault_report.parse_fault_report()

        coverage = \
            fault_report.compute_flist_coverage(fault_list,
                                        self.sff_config,
                                        self.coverage_formula)

        return (test_application_time.pop(), coverage)

    def run(self,
            initial_stl_stats: tuple[int, float],
            times_to_shuffle: int = 100) -> None:

        # Step 1: Compute initial stats of the STL
        initial_tat, coverage = initial_stl_stats
        log.debug(f"Initial coverage {coverage}, TaT {initial_tat}")

        vc_zoix = self.vc_zoix
        fault_report = self.fsim_report

        vc_zoix.create_fcm_script(self.zoix_fcm_file, **self.zoix_fcm_kwargs)

        # Keep a backup of all sources since
        # they will be modified in-place.
        zip_archive("../backup", *[asm.get_asm_source() for asm
                                   in self.assembly_sources])

        all_instructions : list[asm.Codeline] = \
            [(asm_id, codeline) for asm_id, asm in
             enumerate(self.assembly_sources) for codeline in asm.get_code()]

        for i in range(times_to_shuffle):
            random.shuffle(all_instructions)

        # Step 2: Select instructions in a random order
        while len(all_instructions) != 0:

            asm_id, codeline = all_instructions.pop(0)
            asm_source_file = self.assembly_sources[asm_id].get_asm_source()

            print(f"Removing {codeline} of assembly source {asm_source_file}")

            # Step 3: Removal of the selected instruction
            handler = self.assembly_sources[asm_id]
            handler.remove(codeline)

            asm_compilation = \
                compile_assembly(*self.assembly_compilation_instructions)

            if not asm_compilation:

                print(f"Assembly source {asm_source_file} does not compile \
after the removal of: {codeline}.")
                continue

            test_application_time = list()

            if self.zoix_compilation_args:

                comp = vc_zoix.compile_sources(*self.zoix_compilation_args)

                if comp == zoix.Compilation.ERROR:

                    log.critical("Unable to compile HDL sources!")
                    exit(1)

            try:

                lsim = vc_zoix.logic_simulate(*self.zoix_lsim_args,
                                            **self.zoix_lsim_kwargs,
                                            tat_value = test_application_time)

            except zoix.LogicSimulationException:

                log.critical("Unable to perform logic simulation for tat \
computation")
                exit(1)

            if lsim == zoix.LogicSimulation.TIMEOUT:

                raise TimeoutError("Logic simulation timed out")

            # TODO: Continue here...


def main():
    """Sandbox/Testing Env"""

    a0_sources = [ "../cv32e40p/sbst/tests/test1.S"]
    a0_settings = {
        "assembly_compilation_instructions" : ["make -C ../cv32e40p/sbst all"],
        "fsim_fault_summary" : "../cv32e40p/run/vc-z01x/fsim_out_csv_files/DEFAULT_summary.csv",
        "fsim_fault_report"  : "../cv32e40p/run/vc-z01x/fsim_out_csv_files/DEFAULT_faultlist.csv",
        "sff_config" : "../cv32e40p/fsim/config.sff",
        "coverage_formula" : "(DD + DN)/(NA + DA + DN + DD + SU)",
        "vcs_compilation_instructions" : [],
        "logic_simulation_instructions" : ["make -C  ../cv32e40p vcs/sim/gate/shell"],
        "logic_simulation_options" : {
            "timeout" : "20.0",
            "success_regexp" : 're.compile(r"test application time = ([0-9]+)", re.DOTALL)',
            "tat_capture_group" : "1"
        },
        "fcm_file" : "../cv32e40p/fsim/fcm.tcl",
        "fcm_options" : {
            "set_config" : "-global_max_jobs 64",
            "create_testcases" : '-name {"test1"} -exec ${::env(VCS_WORK_DIR)}/simv -args "./simv +firmware=${::env(FIRMWARE)}" -fsim_args "-fsim=fault+dictionary"',
            "fsim" : "-verbose",
            "report" : "-campaign cv32e40p -report fsim_out -csv -overwrite",
        },
        "fault_simulation_instructions" : ["make -C ../cv32e40p vcs/fgen/saf", "make -C ../cv32e40p vcs/fsim/gate/shell"],
        "fault_simulation_options" : {
            "timeout" : "None",
            "allow" : '[re.compile(r"Info\: Connected to started server")]'
        }
    }

    isa = asm.ISA(pathlib.Path("../langs/riscv.isa"))

    A = A0(isa, *a0_sources, **a0_settings)

    tat, coverage = A.pre_run()
    A.run((tat, coverage))

if __name__ == "__main__":
    main()
