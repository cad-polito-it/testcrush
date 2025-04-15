#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import pathlib
import re
import random
import csv
import time
import os

from testcrush.utils import get_logger, compile_assembly, zip_archive, Singleton, addr2line, reap_process_tree
from testcrush import asm, zoix, preprocessor
from typing import Any

log = get_logger()


class CSVCompactionStatistics(metaclass=Singleton):
    """Manages I/O operations on the CSV file which logs the statistics of the A0."""
    _header = ["asm_source", "removed_codeline", "compiles", "lsim_ok",
               "tat", "fsim_ok", "coverage", "verdict"]

    def __init__(self, output: pathlib.Path) -> 'CSVCompactionStatistics':

        self._file = open(output, 'w')
        self.writer: csv._writer = csv.writer(self._file)
        self.writer.writerow(self._header)

    def __iadd__(self, rowline: dict):

        self.writer.writerow(rowline.values())
        self._file.flush()
        return self


class PreprocessorA0(preprocessor.Preprocessor):
    """Preprocessor subclass for A0"""

    def prune_candidates(self, candidates: list[asm.Codeline], mapping: dict[str, str]) -> None:
        """
        Performs Attribute-Trace prunning of the codeline candidates of A0.

        Takes as input the list of ``Codeline`` objects of A0. This list will be modified in-place by identifying the
        relevance of each codeline towards fault detection. The fault attributes of simulation time and program counter
        are accumulated for each prime fault. Then, a query is performed on the trace database for each <time,pc> pair
        in order to extract a window of program counters (i.e., instruction sequences). Then, thes program counters are
        associated with line numbers in the assembly sources and are ommitted from the search space. That is, they are
        removed from the ``candidates`` list which is modified in place.

        Args:
            candidates (list[asm.Codeline]): Reference to the list of candidates of A0. To be modified **in-place**.
            mapping (dict[str, str]): A mapping of Z01X fault attributes to Trace column names.

        """
        # 1. Gather attribute pairs
        attributes = list()
        for fault in self.fault_list:

            if hasattr(fault, "fault_attributes"):

                entry = {self.zoix2trace[k]: fault.fault_attributes[k] for k in self.zoix2trace.keys()}
                if entry not in attributes:

                    attributes.append(entry)

        # 2. Query the database for PC windows
        # TODO: How to specify the column name of the trace? ask explicitly for PC?
        pcs = list()
        for entry in attributes:
            try:
                window = [pc for (pc,) in self.query_trace_db(select="PC", where=entry, history=4)]
            except ValueError:
                continue

            if window not in pcs:
                pcs.append(window)

        # Flatten the list
        pcs = [pc for window in pcs for pc in window]

        # 3. Find the asm source and line numbers and filter out the candidates
        removed = list()
        for pc in pcs:

            asm_file, lineno = addr2line(self.elf, pc)

            if lineno in removed:
                log.warning(f"Line {lineno} has already been removed. Skipping.")
                continue

            if not asm_file:
                log.warning(f"Program counter {pc} not found in {self.elf}")

            if asm_file not in mapping:
                log.warning(f"PC value {pc} maps to line {lineno} of {asm_file} which isn't in asm sources. Skipping.")
                continue

            before = len(candidates)
            candidates[:] = list(filter(lambda entry: not ((entry[0] == mapping[asm_file]) and
                                                           (entry[1] == lineno - 1)),
                                        candidates))
            after = len(candidates)

            if before != after:
                removed.append(lineno)


class A0(metaclass=Singleton):

    """Implements the A0 compaction algorithm"""

    def __init__(self, isa: pathlib.Path, a0_asm_sources: list[str], a0_settings: dict[str, Any]) -> "A0":

        log.debug(f"Generating AssemblyHandlers for {a0_asm_sources}")
        a0_asm_sources = list(map(pathlib.Path, a0_asm_sources))
        self.assembly_sources: list[asm.AssemblyHandler] = [asm.AssemblyHandler(asm.ISA(isa), asm_file,
                                                                                chunksize=1)
                                                            for asm_file in a0_asm_sources]

        # Flatten candidates list
        self.all_instructions: list[tuple[int, asm.Codeline]] = [
            (asm_id, codeline)
            for asm_id, asm in enumerate(self.assembly_sources)
            for codeline in asm.get_code()
        ]

        self.path_to_id = {f"{v.stem}{v.suffix}": k for k, v in enumerate(a0_asm_sources)}

        self.assembly_compilation_instructions: list[str] = a0_settings.get("assembly_compilation_instructions")

        self.zoix_compilation_args: list[str] = a0_settings.get("vcs_compilation_instructions")
        log.debug(f"VCS compilation instructions for HDL sources set to {self.zoix_compilation_args}")

        self.zoix_lsim_args: list[str] = a0_settings.get("vcs_logic_simulation_instructions")
        log.debug(f"VCS logic simulation instructions are {self.zoix_lsim_args}")
        self.zoix_lsim_kwargs: dict[str, float | re.Pattern | int | list] = \
            {k: v for k, v in a0_settings.get("vcs_logic_simulation_control").items()}
        log.debug(f"VCS logic simulation control parameters are: {self.zoix_lsim_kwargs}")

        self.zoix_fsim_args: list[str] = a0_settings.get("zoix_fault_simulation_instructions")
        self.zoix_fsim_kwargs: dict[str, float] = \
            {k: v for k, v in a0_settings.get("zoix_fault_simulation_control").items()}

        self.fsim_report: zoix.TxtFaultReport = zoix.TxtFaultReport(pathlib.Path(a0_settings.get("fsim_report")))
        log.debug(f"Z01X fault report is set to: {self.fsim_report}")
        self.coverage_formula: str = a0_settings.get("coverage_formula")
        log.debug(f"The coverage formula that will be used is: {self.coverage_formula}")

        self.compaction_policy = a0_settings.get("compaction_policy")
        log.debug(f"The compaction policy that will be used is: {self.compaction_policy}")

        self.vc_zoix: zoix.ZoixInvoker = zoix.ZoixInvoker()

    @staticmethod
    def evaluate(previous_result: tuple[int, float],
                 new_result: tuple[int, float]) -> bool:
        """
        Evaluates the new results with respect to the previous ones.

        Specifically, if new tat <= old tat and if new coverage >= old coverage.

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
        Main loop of the A0 algorithm

        1. Removal of a random instruction
        2. Cross-compilation
            2.1 If FAIL, Restore
        3. Logic simulation
            3.1 If ERROR or TIMEOUT, Restore
        4. Fault simulation
            4.1 If ERROR or TIMEOUT, Restore
        5. Evaluation
        6. Goto 1.

        Args:
            initial_stl_stats (tuple[int, float]): The test application time (int) and coverage (float) of the original
                                                   STL
            times_to_shuffle (int, optional): Number of times to permutate the assembly candidates. Defaults to 100.

        Returns:
            None
        """
        def _restore(asm_source: int) -> None:
            """
            Invokes the ``restore()`` function of a specific assembly handler.

            Args:
                asm_source (int): The identifier of the assembly source.

            Returns:
                None
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
        stats_filename = f"a0_statistics_{unique_id}.csv"
        stats = CSVCompactionStatistics(pathlib.Path(stats_filename))

        # Keep a backup of all sources since
        # they will be modified in-place.
        zip_archive(f"../backup_{unique_id}", *[asm.get_asm_source() for asm in self.assembly_sources])

        # Randomize order for Step 2
        for _ in range(times_to_shuffle):
            random.shuffle(self.all_instructions)

        iteration_stats = dict.fromkeys(CSVCompactionStatistics._header)

        iteration_stats["tat"] = initial_tat
        iteration_stats["coverage"] = initial_coverage

        total_iterations = len(self.all_instructions)

        # Step 2: Select instructions in a random order
        old_stl_stats = (initial_tat, initial_coverage)
        while len(self.all_instructions) != 0:

            print(f"""
#############
# ITERATION {total_iterations - len(self.all_instructions) + 1} / {total_iterations}
#############
""")

            # Update statistics
            if any(iteration_stats.values()):
                stats += iteration_stats
                iteration_stats = dict.fromkeys(CSVCompactionStatistics._header)

            asm_id, codeline = self.all_instructions.pop(0)
            asm_source_file = self.assembly_sources[asm_id].get_asm_source().name

            iteration_stats["asm_source"] = asm_source_file
            iteration_stats["removed_codeline"] = codeline

            print(f"Removing {codeline} of assembly source {asm_source_file}")
            # Step 3: Removal of the selected instruction
            handler = self.assembly_sources[asm_id]
            handler.remove(codeline)

            # +-+-+-+ +-+-+-+-+-+-+-+
            # |A|S|M| |C|O|M|P|I|L|E|
            # +-+-+-+ +-+-+-+-+-+-+-+
            print("\tCross-compiling assembly sources.")
            asm_compilation = compile_assembly(*self.assembly_compilation_instructions)

            if not asm_compilation:

                print(f"\t{asm_source_file} does not compile after the removal of: {codeline}. Restoring!")
                iteration_stats["compiles"] = "NO"
                iteration_stats["verdict"] = "Restore"
                _restore(asm_id)
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

                print(f"\tLogic simulation of {asm_source_file} resulted in {lsim.value} after removing {codeline}.")
                print("\tRestoring.")
                iteration_stats["compiles"] = "YES"
                iteration_stats["lsim_ok"] = f"NO-{lsim.value}"
                iteration_stats["verdict"] = "Restore"
                _restore(asm_id)
                continue

            test_application_time = test_application_time.pop(0)

            # +-+-+-+ +-+-+-+-+
            # |V|C|S| |F|S|I|M|
            # +-+-+-+ +-+-+-+-+
            print("\tInitiating fault simulation.")
            fsim = vc_zoix.fault_simulate(*self.zoix_fsim_args, **self.zoix_fsim_kwargs)

            if fsim != zoix.FaultSimulation.SUCCESS:
                print(f"\tFault simulation of {asm_source_file} resulted in a {fsim.value} after removing {codeline}.")
                print("\tRestoring.")
                iteration_stats["compiles"] = "YES"
                iteration_stats["lsim_ok"] = "YES"
                iteration_stats["tat"] = str(test_application_time)
                iteration_stats["fsim_ok"] = f"NO-{fsim.value}"
                iteration_stats["verdict"] = "Restore"
                _restore(asm_id)
                continue

            print("\t\tComputing coverage.")
            coverage = self._coverage()

            new_stl_stats = (test_application_time, coverage)

            iteration_stats["compiles"] = "YES"
            iteration_stats["lsim_ok"] = "YES"
            iteration_stats["tat"] = str(test_application_time)
            iteration_stats["fsim_ok"] = "YES"
            iteration_stats["coverage"] = str(coverage)

            # Step 4: Coverage and TaT evaluation.  Wrt
            # the paper the evaluation happens  on  the
            # coverage i.e., new >= old rather than the
            # comparisson of the set of detected faults
            if self.evaluate(old_stl_stats, new_stl_stats):

                print(f"\tSTL has better stats than before!\n\t\tOld TaT: \
{old_stl_stats[0]} | Old Coverage: {old_stl_stats[1]}\n\t\tNew TaT: \
{new_stl_stats[0]} | New Coverage: {new_stl_stats[1]}\n\tProceeding!")

                if (self.compaction_policy == "Maximize"):
                    old_stl_stats = new_stl_stats
                elif self.compaction_policy == "Threshold":
                    # We want to minimize TaT remaining over the initial faults coverage
                    old_stl_stats = (new_stl_stats[0], old_stl_stats[1])
                else:
                    log.critical("Unknown compaction policy!")
                    exit(1)

                iteration_stats["verdict"] = "Proceed"

            else:

                print(f"\tSTL has worse stats than before!\n\t\tOld TaT: \
{old_stl_stats[0]} | Old Coverage: {old_stl_stats[1]}\n\t\tNew TaT: \
{new_stl_stats[0]} | New Coverage: {new_stl_stats[1]}\n\tRestoring!")

                iteration_stats["verdict"] = "Restore"
                _restore(asm_id)

        # Last iteration updates
        if any(iteration_stats.values()):
            stats += iteration_stats
            iteration_stats = dict.fromkeys(CSVCompactionStatistics._header)

    def post_run(self) -> None:
        """ Cleanup any VC-Z01X stopped processes """
        reap_process_tree(os.getpid())
