#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import pathlib
import re
import random
import csv
import time
import sqlite3
import os
import io

import testcrush.grammars.transformers as transformers
from testcrush.utils import get_logger, compile_assembly, zip_archive, Singleton, reap_process_tree, addr2line
from testcrush import asm, zoix
from typing import Any

log = get_logger()


class CSVCompactionStatistics(metaclass=Singleton):
    """Manages I/O operations on the CSV file which logs the statistics of the A1xx."""
    _header = ["asm_source", "block_index", "removed_codelines", "compiles", "lsim_ok",
               "tat", "fsim_ok", "coverage", "verdict"]

    def __init__(self, output: pathlib.Path) -> 'CSVCompactionStatistics':

        self._file = open(output, 'w')
        self.writer: csv._writer = csv.writer(self._file)
        self.writer.writerow(self._header)

    def __iadd__(self, rowline: dict):

        self.writer.writerow(rowline.values())
        self._file.flush()
        return self


class Preprocessor(metaclass=Singleton):
    """Filters out candidate instructions"""

    _trace_db = ".trace.db"

    def __init__(self, fault_list: list[zoix.Fault], **kwargs) -> 'Preprocessor':

        factory = transformers.TraceTransformerFactory()
        parser = factory(kwargs.get("processor_name"))
        processor_trace = kwargs.get("processor_trace")

        with open(processor_trace) as src:
            trace_raw = src.read()

        self.trace = parser.parse(trace_raw)
        self.fault_list: list[zoix.Fault] = fault_list
        self.elf = kwargs.get("elf_file")
        self.zoix2trace = kwargs.get("zoix_to_trace")

        self._create_trace_db()

    def _create_trace_db(self):
        """
        Transforms the trace of the DUT to a SQLite database of a single table. The header of the CSV is mapped to the
        DB column names and then the CSV body is transformed into DB row entries.
        """

        # If pre-existent db is found, delete it.
        db = pathlib.Path(self._trace_db)
        if db.exists():
            log.debug(f"Database {self._trace_db} exists. Overwritting it.")
            db.unlink()

        con = sqlite3.connect(self._trace_db)
        cursor = con.cursor()

        header: list[str] = self.trace[0].split(',')
        header = list(map(lambda column_name: f"\"{column_name}\"", header))
        header = ", ".join(header)

        cursor.execute(f"CREATE TABLE trace({header})")

        body: list[str] = self.trace[1:]

        with io.StringIO('\n'.join(body)) as source:

            for row in csv.reader(source):

                cursor.execute(f"INSERT INTO trace VALUES ({', '.join(['?'] * len(row))})", row)

        con.commit()
        con.close()

        log.debug(f"Database {self._trace_db} created.")

    def query_trace_db(self, select: str, where: dict[str, str],
                       history: int = 5, allow_multiple: bool = False) -> list[tuple[str, ...]]:
        """
        Perform a query with the specified parameters.

        Assuming that the DB looks like this:

        ::

            Time || Cycle || PC       || Instruction
            -----||-------||----------||------------
            10ns || 1     || 00000004 || and
            20ns || 2     || 00000008 || or          <-*
            30ns || 3     || 0000000c || xor         <-|
            40ns || 4     || 00000010 || sll         <-|
            50ns || 5     || 00000014 || j           <-|
            60ns || 6     || 0000004c || addi        <-*
            70ns || 7     || 00000050 || wfi

        And you perform a query for the ``select="PC"`` and ``where={"PC": "0000004c", "Time": "60ns"}`` then the search
        would result in a window of 1+4 ``PC`` values, indicated by ``<-`` in the snapshot above. The size of the window
        defaults to 5 but can be freely selected by the user.

        Args:
            select (str): The field to select in the query.
            where (dict[str, str]): A dictionary specifying conditions to filter the query.
            history (int, optional): The number of past queries to include. Defaults to 5.
            allow_multiple (bool, optional): Whether to allow multiple results. Defaults to False.

        Returns:
            list[tuple[str, ...]: A list of query results (tuples of strings) matching the criteria.
        """

        db = pathlib.Path(self._trace_db)
        if not db.exists():
            raise FileNotFoundError("Trace DB not found")

        columns = where.keys()

        query = f"""
            SELECT ROWID
            FROM trace
            WHERE {' AND '.join([f'{x} = ?' for x in columns])}
        """

        values = where.values()
        with sqlite3.connect(db) as con:

            cursor = con.cursor()

            cursor.execute(query, tuple(values))
            rowids = cursor.fetchall()

            if not rowids:
                raise ValueError(f"No row found for {', '.join([f'{k}={v}' for k, v in where.items()])}")

            if len(rowids) > 1 and not allow_multiple:
                raise ValueError(f"Query resulted in multiple ROWIDs for \
{', '.join([f'{k}={v}' for k, v in where.items()])}")

            result = list()
            for rowid, in rowids:

                query_with_history = f"""
                    SELECT {'"'+select+'"' if select != '*' else select} FROM trace
                    WHERE ROWID <= ?
                    ORDER BY ROWID DESC
                    LIMIT ?
                """

            cursor.execute(query_with_history, (rowid, history))
            result += cursor.fetchall()[::-1]

            return result

    @staticmethod
    def get_chunked_codelines(candidates: list[tuple[int, asm.Codeline]],
                              chunksize: int) -> list[tuple[int, list[asm.Codeline]]]:
        """
        Divides codelines in chunks, for each file

        Args:
            candidates (list[tuple[int, list(asm.Codeline)]]): Reference to the list of candidates of A1xx
            chunksize (int): Dimension of each slice (except for the last one which may be different)
        """

        # First, group codelines by asm_files
        max_id: int = max(asm_id + 1 for asm_id, _ in candidates)
        grouped_candidates: list[tuple[int, list[asm.Codeline]]] = [(asm_id, []) for asm_id in range(max_id)]

        for (asm_id, codeline) in candidates:
            grouped_candidates[asm_id][1].append(codeline)

        # Recompose as chunks
        chunked_candidates = list()

        for asm_id, candidates in grouped_candidates:

            # Create slice of chunksize dimension
            for i in range(0, len(candidates), chunksize):
                chunked_candidates.append((asm_id, candidates[i:i + chunksize]))

        return chunked_candidates

    def prune_candidates(self, candidates: list[tuple[int, asm.Codeline]], mapping: dict[str, str],
                         chunksize: int) -> list[tuple[int, list[asm.Codeline]]]:
        """
        Performs Attribute-Trace prunning of the codeline candidates of A1xx.

        Takes as input the list of ``Codeline`` objects of A1xx. This list will be modified in-place by identifying the
        relevance of each codeline towards fault detection. The fault attributes of simulation time and program counter
        are accumulated for each prime fault. Then, a query is performed on the trace database for each <time,pc> pair
        in order to extract a window of program counters (i.e., instruction sequences). Then, thes program counters are
        associated with line numbers in the assembly sources and are ommitted from the search space. That is, they are
        removed from the ``candidates`` list which is modified in place.

        Args:
            candidates (list[tuple[int, asm.Codeline]]): Reference to the list of candidates of A1xx.
                To be modified **in-place**.
            mapping (dict[str, str]): A mapping of Z01X fault attributes to Trace column names.
            chunksize: (int): Chunk dimension

        Returns:
            (list[tuple[int, list[asm.Codeline]]]): List of chunks, each associated with its asm_id
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

        return self.get_chunked_codelines(candidates, chunksize)


class A1xx(metaclass=Singleton):

    """Implements the A1xx compaction algorithm"""

    def __init__(self, isa: pathlib.Path, a1xx_asm_sources: list[str], a1xx_settings: dict[str, Any]) -> "A1xx":

        log.debug(f"Generating AssemblyHandlers for {a1xx_asm_sources}")
        a1xx_asm_sources = list(map(pathlib.Path, a1xx_asm_sources))
        self.assembly_sources: list[asm.AssemblyHandler] = [asm.AssemblyHandler(asm.ISA(isa), asm_file,
                                                            chunksize=a1xx_settings.get("a1xx_segment_dimension"))
                                                            for asm_file in a1xx_asm_sources]

        self.all_instructions: list[tuple[int, asm.Codeline]] = [
            (asm_id, codeline)
            for asm_id, asm in enumerate(self.assembly_sources)
            for codeline in asm.get_code()
        ]

        self.all_code_chunks: list[tuple[int, list[asm.Codeline]]] = [
            (asm_id, chunk)
            for asm_id, asm in enumerate(self.assembly_sources)
            for chunk in asm.get_code_chunks()
        ]

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

        self.compaction_policy = a1xx_settings.get("compaction_policy")
        log.debug(f"The compaction policy that will be used is: {self.compaction_policy}")

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
                                                   STL.
            times_to_shuffle (int, optional): Number of times to permutate the assembly candidates. Defaults to 100,
            useful only for the "Random" policy.

        Returns:
            None
        """
        def _restore(asm_source: int, candidate_codelines: list[asm.Codeline]) -> None:
            """
            Invokes the ``restore()`` function of a specific assembly handler.

            Args:
                asm_source (int): The identifier of the assembly source.
                candidate_codelines (list[asm.Codeline]): The list of candidates currently involved
                    in block elimination.

            Returns:
                None
            """
            candidate_codelines.pop()
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

        # Get all the blocks in reverse order
        blocks_number = len(self.all_code_chunks)
        blocks = self.all_code_chunks[::-1]

        log.debug(f"""Code len {len([codeline for chunk in self.all_code_chunks for codeline in chunk[1]])},
                segment_dimension: {self.segment_dimension},
                blocks_number: {blocks_number}
            """)

        for (i, (asm_id, block)) in enumerate(blocks):
            print(f"""
#############
# BLOCK {i + 1}/{blocks_number}
#############
""")

            # Step 4-5: Remove a block of code following the given configurations

            handler = self.assembly_sources[asm_id]
            assembly_source = self.assembly_sources[asm_id].get_asm_source().name

            candidate_codelines = list()
            block_instructions = len(block)

            for _ in range(block_instructions):
                if self.policy == 'B':
                    codeline = block.pop(0)
                elif self.policy == 'F':
                    codeline = block.pop()
                elif self.policy == 'R':
                    codeline = block.pop(random.randint(0, len(block) - 1))
                else:
                    log.fatal("Inexistent policy!")
                    exit(1)

                candidate_codelines.append(codeline)
                handler.remove(codeline)

            for _ in range(block_instructions):

                removed_codelines = ("\n".join(str(codeline) for codeline in candidate_codelines))

                print(f"Removing:{removed_codelines}\n of assembly sources {assembly_source}")

                # Update statistics
                if any(iteration_stats.values()):
                    stats += iteration_stats
                    iteration_stats = dict.fromkeys(CSVCompactionStatistics._header)

                iteration_stats["block_index"] = str(i)
                iteration_stats["asm_source"] = assembly_source
                iteration_stats["removed_codelines"] = "\t".join(str(codeline) for codeline in candidate_codelines)

                # +-+-+-+ +-+-+-+-+-+-+-+
                # |A|S|M| |C|O|M|P|I|L|E|
                # +-+-+-+ +-+-+-+-+-+-+-+
                print("\tCross-compiling assembly sources.")
                asm_compilation = compile_assembly(*self.assembly_compilation_instructions)

                if not asm_compilation:

                    print(f"\tDoes not compile after the removal of: {removed_codelines}. Restoring!")
                    iteration_stats["compiles"] = "NO"
                    iteration_stats["verdict"] = "Restore"

                    _restore(asm_id, candidate_codelines)
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
                    lsim = vc_zoix.logic_simulate(
                        *self.zoix_lsim_args,
                        **self.zoix_lsim_kwargs,
                        tat_value=test_application_time
                    )

                except zoix.LogicSimulationException:

                    log.critical("Unable to perform logic simulation for TaT computation. Simulation status not set!")
                    exit(1)

                if lsim != zoix.LogicSimulation.SUCCESS:

                    print(f"\tLogic simulation resulted in {lsim.value} after removing {removed_codelines}.")
                    print("\tRestoring.")
                    iteration_stats["compiles"] = "YES"
                    iteration_stats["lsim_ok"] = f"NO-{lsim.value}"
                    iteration_stats["verdict"] = "Restore"

                    _restore(asm_id, candidate_codelines)
                    continue

                test_application_time = test_application_time.pop(0)

                # +-+-+-+ +-+-+-+-+
                # |V|C|S| |F|S|I|M|
                # +-+-+-+ +-+-+-+-+
                print("\tInitiating fault simulation.")
                fsim = vc_zoix.fault_simulate(*self.zoix_fsim_args, **self.zoix_fsim_kwargs)

                if fsim != zoix.FaultSimulation.SUCCESS:
                    print(f"\tFault simulation resulted in a {fsim.value} after removing: {removed_codelines}")
                    print("\tRestoring.")
                    iteration_stats["compiles"] = "YES"
                    iteration_stats["lsim_ok"] = "YES"
                    iteration_stats["tat"] = str(test_application_time)
                    iteration_stats["fsim_ok"] = f"NO-{fsim.value}"
                    iteration_stats["verdict"] = "Restore"

                    _restore(asm_id, candidate_codelines)
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

                    if (self.compaction_policy == "Maximize"):
                        old_stl_stats = new_stl_stats
                    elif self.compaction_policy == "Threshold":
                        # We want to minimize TaT remaining over the initial faults coverage
                        old_stl_stats = (new_stl_stats[0], old_stl_stats[1])
                    else:
                        log.critical("Unknown compaction policy!")
                        exit(1)

                    iteration_stats["verdict"] = "Proceed"
                    break

                else:

                    print(f"\tSTL has worse stats than before!\n\t\tOld TaT: \
    {old_stl_stats[0]} | Old Coverage: {old_stl_stats[1]}\n\t\tNew TaT: \
    {new_stl_stats[0]} | New Coverage: {new_stl_stats[1]}\n\tRestoring!")

                    iteration_stats["verdict"] = "Restore"

                    _restore(asm_id, candidate_codelines)

        # Last iteration updates
        if any(iteration_stats.values()):
            stats += iteration_stats
            iteration_stats = dict.fromkeys(CSVCompactionStatistics._header)

    def post_run(self) -> None:
        """ Cleanup any VC-Z01X stopped processes """
        reap_process_tree(os.getpid())
