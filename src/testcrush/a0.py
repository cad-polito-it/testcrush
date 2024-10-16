#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import pathlib
import re
import random
import csv
import time
import lark
import sqlite3
import io

import testcrush.grammars.transformers as transformers
from testcrush.utils import get_logger, compile_assembly, zip_archive, Singleton
from testcrush import asm, zoix
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


class Preprocessor(metaclass=Singleton):
    """Filters out candidate instructions"""

    _trace_db = ".trace.db"

    def __init__(self, txt_fault_report: pathlib.Path, processor_trace: pathlib.Path, **mappings) -> 'Preprocessor':

        factory = transformers.TraceTransformerFactory()
        transformer, grammar = factory(mappings.get("processor_name"))

        with open(processor_trace) as src:
            trace_raw = src.read()

        parser = lark.Lark(grammar=grammar, start="start", parser="lalr", transformer=transformer)
        self.trace = parser.parse(trace_raw)

        factory = transformers.FaultReportTransformerFactory()
        transformer, grammar = factory("FaultList")

        fault_report = zoix.TxtFaultReport(txt_fault_report)
        parser = lark.Lark(grammar=grammar, start="start", parser="lalr", transformer=transformer)
        self.fault_list: list[zoix.Fault] = parser.parse(fault_report.extract("FaultList"))

        self._create_trace_db()

    def _create_trace_db(self):
        """
        Transforms the trace of the DUT to a SQLite database of a single table. The header of the CSV is mapped to the
        DB column names and then the CSV body is transformed into DB row entries.
        """

        # If pre-existent db is found, delete it.
        db = pathlib.Path(self._trace_db)
        if db.exists():
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
                    SELECT {select} FROM trace
                    WHERE ROWID <= ?
                    ORDER BY ROWID DESC
                    LIMIT ?
                """

            cursor.execute(query_with_history, (rowid, history))
            result += cursor.fetchall()[::-1]

            return result

    def prune_candidates(candidates: list[asm.Codeline]):
        # TODO:
        ...


class A0(metaclass=Singleton):

    """Implements the A0 compaction algorithm of https://doi.org/10.1109/TC.2016.2643663"""

    def __init__(self, isa: str, a0_asm_sources: list[str], a0_settings: dict[str, Any]) -> "A0":

        log.debug(f"Generating AssemblyHandlers for {a0_asm_sources}")
        self.assembly_sources: list[asm.AssemblyHandler] = [asm.AssemblyHandler(isa, pathlib.Path(asm_file),
                                                                                chunksize=1)
                                                            for asm_file in a0_asm_sources]

        # Flatten candidates list
        self.all_instructions: list[asm.Codeline] = [(asm_id, codeline) for asm_id, asm in
                                                     enumerate(self.assembly_sources) for codeline in asm.get_code()]
        self.path_to_id = {v: k for k, v in enumerate(a0_asm_sources)}

        self.assembly_compilation_instructions: list[str] = a0_settings.get("assembly_compilation_instructions")
        self.fsim_report: zoix.CSVFaultReport = zoix.CSVFaultReport(
            fault_summary=pathlib.Path(a0_settings.get("csv_fault_summary")),
            fault_report=pathlib.Path(a0_settings.get("csv_fault_report")))

        self.summary_coverage_row: int = a0_settings.get("coverage_summary_row", None)
        self.summary_coverage_col: int = a0_settings.get("coverage_summary_col", None)

        self.sff_config: pathlib.Path = pathlib.Path(a0_settings.get("sff_config"))
        self.coverage_formula: str = a0_settings.get("coverage_formula")
        log.debug(f"Fault reports set to {self.fsim_report=}")

        self.zoix_compilation_args: list[str] = a0_settings.get("vcs_compilation_instructions")
        log.debug(f"VCS Compilation instructions for HDL sources set to {self.zoix_compilation_args}")

        self.zoix_lsim_args: list[str] = a0_settings.get("vcs_logic_simulation_instructions")
        self.zoix_lsim_kwargs: dict[str, float | re.Pattern | int | list] = \
            {k: v for k, v in a0_settings.get("vcs_logic_simulation_control").items()}

        self.zoix_fsim_args: list[str] = a0_settings.get("zoix_fault_simulation_instructions")
        self.zoix_fsim_kwargs: dict[str, float] = \
            {k: v for k, v in a0_settings.get("zoix_fault_simulation_control").items()}

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

    def deduce_coverage(self, precision: int = 4, fault_status_attr: str = "Status") -> float:
        """
        Returns the fault coverage value by selecting one of the two supported coverage extraction methods based on the
        configuration.

        The fault coverage can be computed -or- extracted. If the user has specified custom status group in his sff
        file (safety flow) then its advised to specify the config && coverage formula at the configuration file in order
        for the coverage to be computed. Otherwise, if the default statuses are used and no custom coverage formula
        is specified (manufacturing flow) then its advised to specify a column and a row from the summary csv file to
        extract the coverage value from the summary.csv file.

        Args:
            precision (int, optional): Specifies the precision of the coverage value when this is computed.
            fault_status_attr (str, optional): Indicates which column of the header row of the faultlist.csv file is
                                                specifying the fault status attribute of the fault. As of now the
                                                default column value is "Status". If the user specifies otherwise in the
                                                configuration file then this value shall be used instead.

        Returns:
            float: The fault coverage.
        """
        coverage = None

        if self.sff_config.exists() and self.coverage_formula != "":

            fault_list = self.fsim_report.parse_fault_report()
            coverage = self.fsim_report.compute_flist_coverage(fault_list,
                                                               self.sff_config,
                                                               self.coverage_formula,
                                                               precision,
                                                               fault_status_attr)

        else:
            coverage = self.fsim_report.extract_summary_cells_from_row(self.summary_coverage_row,
                                                                       self.summary_coverage_col).pop()
            if '%' in coverage:
                coverage = float(coverage.replace('%', ''))

        return coverage

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

        coverage = self.deduce_coverage()

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
            coverage = self.deduce_coverage()

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

                old_stl_stats = new_stl_stats
                iteration_stats["verdict"] = "Proceed"

            else:

                print(f"\tSTL has worse stats than before!\n\t\tOld TaT: \
{old_stl_stats[0]} | Old Coverage: {old_stl_stats[1]}\n\t\tNew TaT: \
{new_stl_stats[0]} | New Coverage: {new_stl_stats[1]}\n\tRestoring!")

                iteration_stats["verdict"] = "Restore"
                _restore(asm_id)
