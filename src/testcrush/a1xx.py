#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import pathlib
import re
import random
import csv
import time
# import sqlite3
import io
import os

import testcrush.grammars.transformers as transformers
from testcrush.utils import get_logger, compile_assembly, zip_archive, Singleton, addr2line, reap_process_tree
from testcrush import asm, zoix
from typing import Any

class CSVCompactionStatistics(metaclass=Singleton):
    """Manages I/O operations on the CSV file which logs the statistics of the A1xx."""
    _header = ["asm_source", "removed_codelines", "compiles", "lsim_ok",
               "tat", "fsim_ok", "coverage", "verdict"]

    def __init__(self, output: pathlib.Path) -> 'CSVCompactionStatistics':

        self._file = open(output, 'w')
        self.writer: csv._writer = csv.writer(self._file)
        self.writer.writerow(self._header)

    def __iadd__(self, rowline: dict):

        self.writer.writerow(rowline.values())
        self._file.flush()
        return self




class A1xx(metaclass=Singleton):

    """Implements the A1xx compaction algorithm"""

    def __init__(self, isa: pathlib.Path, a1xx_asm_sources: list[str], a1xx_settings: dict[str, Any]) -> "A1xx":

        log.debug(f"Generating AssemblyHandlers for {a1xx_asm_sources}")
        a1xx_asm_sources = list(map(pathlib.Path, a1xx_asm_sources))
        self.assembly_sources: list[asm.AssemblyHandler] = [asm.AssemblyHandler(asm.ISA(isa), asm_file,
                                                                                chunksize=1)
                                                            for asm_file in a1xx_asm_sources]

        # Flatten candidates list
        self.all_instructions: list[asm.Codeline] = [(asm_id, codeline) for asm_id, asm in
                                                     enumerate(self.assembly_sources) for codeline in asm.get_code()]
        self.path_to_id = {f"{v.stem}{v.suffix}": k for k, v in enumerate(a1xx_asm_sources)}

        self.assembly_compilation_instructions: list[str] = a1xx_settings.get("assembly_compilation_instructions")

        self.zoix_compilation_args: list[str] = a1xx_settings.get("vcs_compilation_instructions")
        log.debug(f"VCS compilation instructions for HDL sources set to {self.zoix_compilation_args}")

        self.zoix_lsim_args: list[str] = a1xx_settings.get("vcs_logic_simulation_instructions")
        log.debug(f"VCS logic simulation instructions are {self.zoix_lsim_args}")
        self.zoix_lsim_kwargs: dict[str, float | re.Pattern | int | list] = \
            {k: v for k, v in a1xx_settings.get("vcs_logic_simulation_control").items()}
        log.debug(f"VCS logic simulation control parameters are: {self.zoix_lsim_kwargs}")

        self.zoix_fsim_args: list[str] = a1xx_settings.get("zoix_fault_simulation_instructions")
        self.zoix_fsim_kwargs: dict[str, float] = \
            {k: v for k, v in a1xx_settings.get("zoix_fault_simulation_control").items()}

        self.fsim_report: zoix.TxtFaultReport = zoix.TxtFaultReport(pathlib.Path(a1xx_settings.get("fsim_report")))
        log.debug(f"Z01X fault report is set to: {self.fsim_report}")
        self.coverage_formula: str = a1xx_settings.get("coverage_formula")
        log.debug(f"The coverage formula that will be used is: {self.coverage_formula}")

        self.segment_dimension = a1xx.settings.get("a1xx_segment_dimension")
        self.policy = a1xx.settings.get("a1xx_policy")


        self.vc_zoix: zoix.ZoixInvoker = zoix.ZoixInvoker()


    @staticmethod
    def evaluate(previous_result: tuple[int, float, list[zoix.Fault]],
                 new_result: tuple[int, float, list[zoix.Fault]]) -> bool:
        """
        Evaluates the new results with respect to the previous ones.

        Specifically, if new tat <= old tat, if new coverage >= old coverage and
        if the faults set of the block are all detected from the code without that block.

        Args:
            previous_result (tuple[int, float]): the old tat value (int) and coverage (float) values.
            new_result (tuple[int, float]): the new tat value (int) and coverage values.

        Returns:
            bool: ``True`` if new tat <= old tat and new coverage >= old coverage. ``False`` otherwise
        """

        old_tat, old_coverage, old_faults_list = previous_result
        new_tat, new_coverage, new_faults_list = new_result

        return (new_tat <= old_tat) and (new_coverage >= old_coverage) and all(fault in new_faults_list for fault in old_faults_list)

    def _coverage(self, precision: int = 4) -> float:
        """
        Args:
            precision (int, optional): Specifies the precision of the coverage value when this is computed.
            fault_status_attr (str, optional): Indicates which column of the header row of the faultlist.csv file is
                                                specifying the fault status attribute of the fault. As of now the
                                                default column value is "Status". If the user specifies otherwise in the
                                                configuration file then this value shall be used instead.

        Returns:
            float: The fault coverage.
        """
        coverage_formula = self.coverage_formula
        return self.fsim_report.compute_coverage(requested_formula=coverage_formula, precision=precision)

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

        test_application_time = list()

        compile_assembly(*self.assembly_compilation_instructions)

        if self.zoix_compilation_args:

            comp = vc_zoix.compile_sources(*self.zoix_compilation_args)

            if comp == zoix.Compilation.ERROR:

                log.critical("Unable to compile HDL sources!")
                exit(1)

        print("Initial logic simulation for TaT computation.")
        try:

            lsim = vc_zoix.logic_simulate(*self.zoix_lsim_args,
                                          **self.zoix_lsim_kwargs,
                                          tat_value=test_application_time)

        except zoix.LogicSimulationException:

            log.critical("Unable to perform logic simulation for TaT computation")
            exit(1)

        if lsim != zoix.LogicSimulation.SUCCESS:

            log.critical("Error during initial logic simulation! Check the debug log!")
            exit(1)

        print("Initial fault simulation for coverage computation.")

        fsim = vc_zoix.fault_simulate(*self.zoix_fsim_args, **self.zoix_fsim_kwargs)

        if fsim != zoix.FaultSimulation.SUCCESS:

            log.critical("Error during initial fault simulation! Check the debug log!")
            exit(1)

        coverage = self._coverage()

        return (test_application_time.pop(), coverage)
    
    def run(self, initial_stl_stats: tuple[int, float]) -> None:
        """
        Main loop of the A1xx algorithm
        
        1. Removal of an instruction block from the last lines of code to index 0
            1.1 Get the set of faults detected in that block
        2. Cross-compilation
            2.1 If FAIL, Restore 
        3. Logic simulation
            3.1 If ERROR, Restore
        4. Fault simulation
            4.1 If ERROR or TIMEOUT, Restore 
        5. Evaluation
        6. Goto 1.

        The restore procedure depends of the configured policy: Forward, Back or Random

        Args:
            initial_stl_stats (tuple[int, float]): The test application time (int) and coverage (float) of the original
                                                   STL

        Returns:
            None
        """
        def _restore(asm_source) -> None:
            """
            Invokes the ``restore()`` function of a specific assembly handler.
            """
            self.assembly_sources[asm_source].restore()
        

        # To be used for generated file suffixes
        unique_id = time.strftime("%d_%b_%H%M", time.gmtime())

        # Step 1: Compute initial stats of the STL
        initial_tat, initial_coverage = initial_stl_stats
        log.debug(f"Initial coverage {initial_coverage}, TaT {initial_tat}")

        # Z01X alias
        vc_zoix = self.vc_zoix

        # Statistics
        stats_filename = f"a1{self.policy}{self.segment_dimension}_statistics_{unique_id}.csv"
        stats = CSVCompactionStatistics(pathlib.Path(stats_filename))

        # Keep a backup of all sources since
        # they will be modified in-place.
        zip_archive(f"../backup_{unique_id}", *[asm.get_asm_source() for asm in self.assembly_sources])

        # Set initial stats
        iteration_stats = dict.fromkeys(CSVCompactionStatistics._header)

        iteration_stats["tat"] = initial_tat
        iteration_stats["coverage"] = initial_coverage        

        # We can not know total_iteration a priori, so in A1xx we don't calculate total_iterations

        # ! TO FINISH

        


    def post_run(self) -> None:
        """ Cleanup any VC-Z01X stopped processes """
        reap_process_tree(os.getpid())

