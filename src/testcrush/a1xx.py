#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import pathlib
import math
import re
import random
import csv
import time
import sqlite3
import io
import os

import testcrush.grammars.transformers as transformers
from testcrush.utils import get_logger, compile_assembly, zip_archive, Singleton, addr2line, reap_process_tree
from testcrush import asm, zoix
from typing import Any

log = get_logger()

class CSVCompactionStatistics(metaclass=Singleton):
    """Manages I/O operations on the CSV file which logs the statistics of the A1xx."""
    _header = ["asm_sources", "block", "removed_codelines", "compiles", "lsim_ok",
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
        self.all_instructions: list[tuple[int, asm.Codeline]] = [(asm_id, codeline) for asm_id, asm in
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

        self.segment_dimension = a1xx_settings.get("a1xx_segment_dimension")
        self.policy = a1xx_settings.get("a1xx_policy")


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

        old_tat, old_coverage = previous_result
        new_tat, new_coverage = new_result

        return (new_tat <= old_tat) and (new_coverage >= old_coverage) 

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
    
    def run(self, initial_stl_stats: tuple[int, float], times_to_shuffle: int = 100) -> None:
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
        def _restore(asm_source, codelines: list[asm.Codeline]) -> None:
            """
            Invokes the ``restore()`` function of a specific assembly handler.
            """
            codelines.pop()
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

        old_stl_stats = (initial_tat, initial_coverage)

        # Step 2: Split code into m (where m = ⌈len(self.all_instructions)/self.segment_dimension)⌉ segments
        m = math.ceil(len(self.all_instructions)/self.segment_dimension)
        # Get all the blocks in reverse order
        blocks =  [self.all_instructions[(i)*self.segment_dimension : (i+1)*self.segment_dimension] for i in range(m)][::-1]

        print(f"Code len {len(self.all_instructions)}, segment {self.segment_dimension}, m: {m}")


        for (i, block) in enumerate(blocks):
            print(f"""
#############
# BLOCK {i} 
#############
""")
    

            # Step 4-5: Remove a block of code following the given configurations

            asm_ids = set()
            codelines = list()
            iteration = len(block)
        
            for j in range(iteration):
                if self.policy == 'B':                    
                    asm_id, codeline = block.pop(0)
                elif self.policy == 'F':
                    asm_id, codeline = block.pop()
                    block.pop()
                elif self.policy == 'R': 
                    asm_id, codeline = block.pop(random.randint(0, len(block) - 1))
                else:
                    log.fatal("Inexistent policy!")
                    exit(1)
    

                codelines.append(codeline)
                asm_ids.add(asm_id)
                handler = self.assembly_sources[asm_id]
                handler.remove(codeline)


            assembly_sources = " ".join(self.assembly_sources[asm_id].get_asm_source().name for asm_id in asm_ids)

            for _ in range(iteration):
                
                print(f"Removing: {"\n".join(str(codeline) for codeline in codelines)}\n of assembly sources {assembly_sources}")
                # Update statistics

                if any(iteration_stats.values()):
                    stats += iteration_stats
                    iteration_stats = dict.fromkeys(CSVCompactionStatistics._header)

                iteration_stats["block"] = str(i)
                iteration_stats["asm_sources"] = " ".join(str(asm_id) for asm_id in asm_ids)
                iteration_stats["removed_codelines"] = "\t".join(str(codeline) for codeline in codelines)


                # +-+-+-+ +-+-+-+-+-+-+-+
                # |A|S|M| |C|O|M|P|I|L|E|
                # +-+-+-+ +-+-+-+-+-+-+-+
                print("\tCross-compiling assembly sources.")
                asm_compilation = compile_assembly(*self.assembly_compilation_instructions)

                if not asm_compilation:

                    print(f"\tDoes not compile after the removal of: {codelines}. Restoring!")
                    iteration_stats["compiles"] = "NO"
                    iteration_stats["verdict"] = "Restore"
                    
                    _restore(asm_id, codelines)
                    continue

                # +-+-+-+ +-+-+-+-+-+-+-+
                # |V|C|S| |C|O|M|P|I|L|E|
                # +-+-+-+ +-+-+-+-+-+-+-+
                if self.zoix_compilation_args:

                    comp = vc_zoix.compile_sources(*self.zoix_compilation_args)

                    if comp == zoix.Compilation.ERROR:

                        log.critical("Unable to compile HDL sources!")
                        exit(1)

                # +-+-+-+ +-+-+-+-+
                # |V|C|S| |L|S|I|M|
                # +-+-+-+ +-+-+-+-+
                test_application_time = list()
                try:
                    print("\tInitiating logic simulation.")
                    lsim = vc_zoix.logic_simulate(*self.zoix_lsim_args,
                                                **self.zoix_lsim_kwargs,
                                                tat_value=test_application_time)

                except zoix.LogicSimulationException:

                    log.critical("Unable to perform logic simulation for TaT computation. Simulation status not set!")
                    exit(1)

                if lsim != zoix.LogicSimulation.SUCCESS:

                    print(f"\tLogic simulation resulted in {lsim.value} after removing {codelines}.")
                    print("\tRestoring.")
                    iteration_stats["compiles"] = "YES"
                    iteration_stats["lsim_ok"] = f"NO-{lsim.value}"
                    iteration_stats["verdict"] = "Restore"

                    _restore(asm_id, codelines)
                    continue

                test_application_time = test_application_time.pop(0)

                # +-+-+-+ +-+-+-+-+
                # |V|C|S| |F|S|I|M|
                # +-+-+-+ +-+-+-+-+
                print("\tInitiating fault simulation.")
                fsim = vc_zoix.fault_simulate(*self.zoix_fsim_args, **self.zoix_fsim_kwargs)

                if fsim != zoix.FaultSimulation.SUCCESS:
                    print(f"\tFault simulation resulted in a {fsim.value} after removing: {"\n".join(str(codeline) for codeline in codelines)}.")
                    print("\tRestoring.")
                    iteration_stats["compiles"] = "YES"
                    iteration_stats["lsim_ok"] = "YES"
                    iteration_stats["tat"] = str(test_application_time)
                    iteration_stats["fsim_ok"] = f"NO-{fsim.value}"
                    iteration_stats["verdict"] = "Restore"

                    _restore(asm_id, codelines)
                    continue

                print("\t\tComputing coverage.")
                coverage = self._coverage()

                new_stl_stats = (test_application_time, coverage)

                iteration_stats["compiles"] = "YES"
                iteration_stats["lsim_ok"] = "YES"
                iteration_stats["tat"] = str(test_application_time)
                iteration_stats["fsim_ok"] = "YES"
                iteration_stats["coverage"] = str(coverage)
                

                # Step 7: Coverage and TaT evaluation.  Wrt
                # the paper the evaluation happens  on  the
                # coverage i.e., new >= old rather than the
                # comparison of the set of detected faults
                if self.evaluate(old_stl_stats, new_stl_stats):

                    print(f"\tSTL has better stats than before!\n\t\tOld TaT: \
    {old_stl_stats[0]} | Old Coverage: {old_stl_stats[1]}\n\t\tNew TaT: \
    {new_stl_stats[0]} | New Coverage: {new_stl_stats[1]}\n\tProceeding!")

                    old_stl_stats = new_stl_stats
                    iteration_stats["verdict"] = "Proceed"
                    break

                else:

                    print(f"\tSTL has worse stats than before!\n\t\tOld TaT: \
    {old_stl_stats[0]} | Old Coverage: {old_stl_stats[1]}\n\t\tNew TaT: \
    {new_stl_stats[0]} | New Coverage: {new_stl_stats[1]}\n\tRestoring!")

                    iteration_stats["verdict"] = "Restore"
                    
                    _restore(asm_id, codelines)
        
        # Last iteration updates
        if any(iteration_stats.values()):
            stats += iteration_stats
            iteration_stats = dict.fromkeys(CSVCompactionStatistics._header)


    def post_run(self) -> None:
        """ Cleanup any VC-Z01X stopped processes """
        reap_process_tree(os.getpid())

