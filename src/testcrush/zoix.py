#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import subprocess
import re
import enum
import pathlib

from testcrush.utils import get_logger, to_snake_case
from typing import Any

log = get_logger()


class Compilation(enum.Enum):
    """Statuses for the VCS compilation of HDL sources."""
    ERROR = "ERROR"  # stderr contains text
    SUCCESS = "SUCCESS"  # None of the above


class LogicSimulation(enum.Enum):
    """Statuses for the simv logic simulation of a given program."""
    TIMEOUT = "TIMEOUT"  # Endless loop
    SIM_ERROR = "ERROR"  # stderr contains text
    SUCCESS = "SUCCESS"  # None of the above


class LogicSimulationException(BaseException):
    """Custom exception for the simv logic simulation."""
    def __init__(self, message="Error during VC Logic Simulation"):
        self.message = message
        super().__init__(self.message)


class FaultSimulation(enum.Enum):
    """Statuses for the Z01X fault simulation."""
    TIMEOUT = "TIMEOUT"  # Wall-clock
    FSIM_ERROR = "ERROR"  # stderr contains text
    SUCCESS = "SUCCESS"  # None of the above


class Fault:
    """
    Generic representation of a **prime** fault

    Each prime fault has two static attributes which are:
    -``equivalent_faults`` (int): Corresponds to the total number of faults equivalent to this fault. Defaults to 1 i.e.
    itself.
    -``equivalent_to`` (Fault): A reference to the primary fault with which the current fault is equivalent. If the
    current fault is prime. Defaults to ``None``.

    When a fault is constructed it corresponds to a prime fault. It is up to the user to resolve any fault equivalence
    by modifying the aforementioned attributes.
    """

    def __init__(self, **fault_attributes: dict[str, Any]) -> 'Fault':

        for attribute, value in fault_attributes.items():
            setattr(self, attribute.replace(" ", "_"), value)

        self.equivalent_faults: int = 1
        self.equivalent_to: Fault = None

    def __repr__(self):
        attrs = ', '.join(f'{key}={value!r}' for key, value in self.__dict__.items()
                          if key not in ("equivalent_faults", "equivalent_to"))  # Avoid recursive reprs
        return f'{self.__class__.__name__}({attrs})'

    def __str__(self):
        return ', '.join(f'{key}: {value}' for key, value in self.__dict__.items()
                         if key not in ("equivalent_faults", "equivalent_to"))  # Avoid recursive reprs

    def __eq__(self, other):

        if isinstance(other, Fault):
            return self.__dict__ == other.__dict__

        return False

    def set(self, attribute: str, value: Any) -> None:

        setattr(self, attribute, value)

    def get(self, attribute: str, default: str | None = None) -> str | Any:
        """
        Generic getter method for arbitrary attribute.

        Args:
            attribute (str): The requested attribute of the fault.
            default (str | None): A default value to be used as a guard.

        Returns:
            str | Any: The fault attribute. If no cast has been performed on
            the attribute then the default type is ``str``.
        """

        return getattr(self, attribute.replace(" ", "_"), default)

    def cast_attribute(self, attribute: str, func: callable) -> None:
        """
        Casts the type of the internal attribute

        Args:
            attribute (str): The requested attribute of the fault to be casted.
            func (callable): A function to cast the fault attribute.

        Returns:
            None

        Raises:
            KeyError: If the requested attribute does not exist.
            ValueError: If the cast cannot be performed e.g., when
                       ``int('a')``.
        """

        attribute = attribute.replace(" ", "_")
        try:
            self.__dict__[attribute] = func(getattr(self, attribute))

        except KeyError:
            log.error(f"Attribute {attribute} not a member of {self.__class__}")

        except ValueError:
            log.critical(f"Unable to cast to {repr(func)} of attribute {getattr(self, attribute)}")
            exit(1)

    def is_prime(self) -> bool:
        """
        Checks whether the fault is a prime fault, i.e., is not equivalent to any other fault.

        Returns:
            bool: True if fault is prime. False otherwise.
        """
        return self.equivalent_to is None


class TxtFaultReport:
    """
    Manages the VC-Z01X text report.
    """
    __slots__ = ["fault_report_path", "fault_report", "fault_list", "status_groups", "coverage"]

    def __init__(self, fault_report: pathlib.Path) -> "TxtFaultReport":
        self.fault_report_path = fault_report  # Store the path, but don't read the file yet
        self.fault_report = None
        self.fault_list = None
        self.status_groups = None
        self.coverage = None

    def __str__(self) -> str:

        return f"{self.fault_report_path.resolve()}"

    def _load_fault_report(self):
        """Load the fault report from the file."""
        if not self.fault_report_path.exists():
            raise FileNotFoundError(f"Fault report file {self.fault_report_path} not found.")

        with open(self.fault_report_path) as src:
            self.fault_report = src.read()

    def _parse_sections(self):
        """Parse the required sections from the fault report."""
        # Ensure the fault report is loaded before parsing
        if self.fault_report is None:
            raise ValueError("Fault report is not loaded.")

        # Lazy import to avoid circular dependencies
        from testcrush.grammars.transformers import FaultReportTransformerFactory

        factory = FaultReportTransformerFactory()
        for section in ["StatusGroups", "Coverage", "FaultList"]:
            parser = factory(section)

            try:
                raw_section = self.extract(section)
            except ValueError:  # section doesn't exist
                setattr(self, to_snake_case(section), None)
                continue

            log.debug(f"Parsing {section}")
            setattr(self, to_snake_case(section), parser.parse(raw_section))

    def update(self):
        """Update and parse all sections once the fault report file is available."""
        self._load_fault_report()  # Read the file
        self._parse_sections()  # Parse all sections

    def extract(self, section: str) -> str:
        """
        Extracts a section of the fault report.

        Args:
            section (str): The case-sensitive section name. E.g., ``Coverage``, ``FaultList``

        Returns:
            str: A newline-joined string of the extracted section (section name included).

        Raises:
            ValueError: If ``section`` does not exist in the fault report.
        """
        extracted_lines = list()

        # Loop control
        section_found: bool = False
        brackets_cc: int = 0

        lines = self.fault_report.splitlines()

        for line in lines:

            if not line:
                continue

            if section in line and "{" in line:
                log.debug(f"Found Section {section} - {line=}")
                section_found = True

            if not section_found:
                continue

            if section_found:

                if '{' in line:
                    brackets_cc += 1
                if '}' in line:
                    brackets_cc -= 1

                extracted_lines.append(fr'{line}')

                if brackets_cc == 0:
                    break

        if not section_found:
            log.debug(f"Requested section \"{section}\" not found!")
            raise ValueError(f"Requested section \"{section}\" not found!")

        return '\n'.join(extracted_lines)

    def compute_coverage(self, requested_formula: str = None, precision: int = 4) -> dict[str, float] | float:
        """
        Manually computes the coverage based on the current fault report.

        Args:
            requested_formula (str, optional): The name of the coverage formula from the ``Coverage {}`` section of the
                                               fault report. Defaults to None.
            precision (int, optional): The requested float precision. Defaults to 4.

        Returns:
            dict[str, float] | float: If no formula name is provided, returns a dictionary mapping formula names to
            their corresponding evaluated coverage values as floats. If a formula name is specified, returns only
            the evaluated value for that formula.

        .. todo::
            * Implement default Test/Fault coverage computation per-Z01X if no ``Coverage{}`` section exists.
        """
        log.info(f"Computing coverage {requested_formula}.")
        self.update()

        retval = list()

        fault_statusses = dict()
        for fault in self.fault_list:

            status = fault.fault_status

            if status in fault_statusses:
                fault_statusses[status] += 1
            else:
                fault_statusses[status] = 1

        status_groups = dict()
        if self.status_groups:

            for group, statuses in self.status_groups.items():

                status_groups[group] = 0

                for status in statuses:

                    if status in fault_statusses:

                        status_groups[group] += fault_statusses[status]

        # We expect that if a coverage formula is specified
        # i.e., Coverage{} exists, then there  may  be some
        # variables there which may not  exist in  statuses
        # or groups. Hence we must set them to 0.
        non_present = dict()
        if self.coverage:

            for formula_name, formula in self.coverage.items():

                for status_or_group in re.findall(r"[A-Z]{2}", formula):

                    if status_or_group not in fault_statusses and status_or_group not in status_groups:

                        non_present[status_or_group] = 0

                retval.append((formula_name,
                               round(eval(formula, {**fault_statusses, **status_groups, **non_present}),
                                     precision)))

        # Else: TODO: Implement default coverage computation according to manual
        return dict(retval)[requested_formula] if requested_formula else dict(retval)


class ZoixInvoker:
    """A wrapper class to be used in handling calls to VCS-Z01X."""
    def __init__(self) -> "ZoixInvoker":
        ...

    @staticmethod
    def execute(instruction: str, timeout: float = None) -> tuple[str, str]:
        """
        Executes a **bash** instruction and returns the ``stdout`` and ``stderr`` responses as a tuple.

        Args:
            instruction (str): The bash instruction to be executed.

        Returns:
            tuple(str, str): The stdout (index 0) and the stderr (index 1)
            as strings.
        """

        log.debug(f"Executing {instruction}...")

        with subprocess.Popen(["/bin/bash", "-c", instruction],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True) as process:

            try:

                stdout, stderr = process.communicate(timeout=timeout)
                return stdout, stderr

            except subprocess.TimeoutExpired:

                log.debug(f"TIMEOUT during the execution of:\n\t{instruction}")
                process.kill()
                return "TimeoutExpired", "TimeoutExpired"

    def compile_sources(self, *instructions: str) -> Compilation:
        """
        Performs compilation of HDL files

        Args:
            instructions (str): A variadic number of bash shell instructions

        Returns:
            Compilation: A status Enum to signify the success or failure of the compilation.

                - ERROR: if any text was found in the ``stderr`` stream during the execution of an instruction.
                - SUCCESS: otherwise.
        """

        compilation_status = Compilation.SUCCESS

        for cmd in instructions:

            stdout, stderr = self.execute(cmd)

            if stderr:

                compilation_status = Compilation.ERROR
                break

        return compilation_status

    def logic_simulate(self, *instructions: str, **kwargs) -> LogicSimulation:
        """
        Performs logic simulation of user-defined firmware and captures the test application time.

        A timeout value must be specified in order to avoid endless loops that will hang the program. There are
        two important kwargs that the user must specify. The success regexp and the tat regexp. During a logic
        simulation, the simulator typically stops when a ``$finish`` call is met. However, in a non-trivial DUT case
        like e.g., a processor, there are many things that may go wrong like for instance an out-of-bounds read or
        write from/to a memory. In that case, it is up to the designer to handle accordingly the situation e.g., issue
        a ``$fatal`` call. Which means, that in order to be accurate and know whether the logic simulation terminates
        gracefully, some sort of ``$display`` must be specified -or- at least the ``$finish`` statement must be invoked
        from the correct place. For this reason, the success regexp is required in order to know that not only the logic
        simulation ended but that it also ended without causing any kind of violation in the DUT.

        When it comes to the tat regexp, this can be either a custom message again issued by the testbench or the time
        of the simulation that the correct ``$finish`` statement was issued. It is up to the user to specify it. However
        in order for the logic simulation to be considerred successful the success regexp AND the tat regexp must match
        something.


        Args:
            instructions (str): A variadic number of bash instructions
            kwargs: User-defined options needed for the evaluation of the result of the logic simulation.
                    These options are:

                - **timeout** (float): A timeout in **seconds** to be used for **each** of the executed logic
                  simulation instructions.

                - **simulation_ok_regex** (re.Pattern): A regular expression used for matching in every line of the
                  ``stdout`` stream to mark the successful completion of the logic simulation.

                - **test_application_time_regex** (re.Pattern): A regular expression used to match the line that reports
                  the test application time from the simulator.

                - **test_application_time_regex_group_no** (int): The index of the capture group in the custom regular
                  expression for the TaT value. Default is 1, corresponding to the ``success_regexp`` group.

                - **tat_value** (list): An **empty** list to store the TaT value after being successfully matched with
                  ``success_regexp``. The list is used to mimic a pass-by-reference.

        Returns:
            LogicSimulation: A status Enum which is:

                - TIMEOUT: if user defined timeout has been triggered.
                - SIM_ERROR: if any text was found in the ``stderr`` stream during the execution of an instruction.
                - SUCCESS: if the halting regexp matched text from the ``stdout`` stream.
        """

        timeout: float = kwargs.get("timeout", None)

        # The default regexp catches the line:
        # $finish at simulation time  XXXXXXYs
        # where X = a digit and Y = time unit.
        # Capturing of the simulation duration
        # done for possible TaT purposes. NOTE
        # that it is advised that BOTH regular
        # expressions ARE specified and   that
        # the default value is not  used. That
        # is because it may be that the TB may
        # have >=1 $finish call locations e.g.
        # on an out-of-bounds read/write case.
        # Hence, be as accurate as possible!!!
        default_regexp = re.compile(r"\$finish[^0-9]+([0-9]+)[m|u|n|p]s", re.DOTALL)

        success_regexp: re.Pattern = kwargs.get("simulation_ok_regex", default_regexp)
        tat_regexp: re.Pattern = kwargs.get("test_application_time_regex", default_regexp)

        # By default, a single capturing  group
        # is expected in the regexp, which maps
        # to the TaT value. If a custom  regexp
        # is provided however, with >1  groups,
        # then the user must specify  which  is
        # the expected capture group.
        tat_capture_group: int = kwargs.get("test_application_time_regex_group_no", 1)

        # An empty mutable container is expected
        # to store the TaT  value  matched  from
        # the regexp. It is used  like  that  to
        # mimic  pass-by-reference and not alter
        # the function's return value.
        tat_value: list = kwargs.get("tat_value", [])

        simulation_status = None

        # Loop control flags
        exit_success = False
        tat_success = False

        for cmd in instructions:

            stdout, stderr = self.execute(cmd, timeout=timeout)

            if stderr and stderr != "TimeoutExpired":

                log.debug(f"Error during execution of {cmd}\n\
                ------[STDERR STREAM]------\n\
                {'-'.join(stderr.splitlines(keepends=True))}\n\
                ---------------------------\n")

                simulation_status = LogicSimulation.SIM_ERROR
                break

            elif stderr == stdout == "TimeoutExpired":

                simulation_status = LogicSimulation.TIMEOUT
                break

            for line in stdout.splitlines():

                log.debug(f"{cmd}: {line.rstrip()}")

                # Exit success
                success_match: re.Match = re.search(success_regexp, line)

                if success_match:
                    log.debug(f"Exit Success: {success_match.groups()}")
                    exit_success = True

                # TaT matching
                tat_match: re.Match = re.search(tat_regexp, line)

                if tat_match:

                    test_application_time = tat_match.group(tat_capture_group)
                    try:
                        tat_value.append(int(test_application_time))
                        tat_success = True
                    except ValueError:
                        raise LogicSimulationException(f"Test application time was not correctly captured \
{test_application_time=} and could not be converted to an integer. Perhaps there is something wrong with your regular \
expression '{tat_regexp}' ?")

                    log.debug(f"TaT Captured: {tat_match.groups()}")

                if tat_success and exit_success:
                    break

        if tat_success and exit_success:

            log.debug(f"Simulation Success! {exit_success=} and {tat_success=}.")
            simulation_status = LogicSimulation.SUCCESS

        elif not (tat_success and exit_success) and simulation_status != LogicSimulation.TIMEOUT:
            log.debug(f"Simulation Failed! {exit_success=} and {tat_success=}.")
            simulation_status = LogicSimulation.SIM_ERROR

        return simulation_status

    def fault_simulate(self, *instructions: str, **kwargs) -> FaultSimulation:
        """
        Performs fault simulation of a user-defined firmware.

        Args:
            instructions (str): A variadic number of shell instructions
                                to invoke Z01X.
            kwargs: User-defined options for fault simulation control.

                - timeout (float): A timeout in **seconds** for each fsim
                  instruction.
                - allow_regexs (list[re.Pattern]): Series of regexps to look for in
                  ``stderr`` and allow continuation without raising any error
                  messages.

        Returns:
            FaultSimulation: A status Enum which is:

                - TIMEOUT: if the timeout kwarg was provided and some
                  instruction exceeded it.
                - FSIM_ERROR: if the ``stderr`` stream contains text during the
                  execution of an instruction.
                - SUCCESS: if none of the above.
        """

        fault_simulation_status = FaultSimulation.SUCCESS

        timeout: float = kwargs.get("timeout", None)
        allow: list[re.Pattern] = kwargs.get("allow_regexs", None)

        for cmd in instructions:

            stdout, stderr = self.execute(cmd, timeout=timeout)

            if stderr and stderr != "TimeoutExpired":

                if allow:

                    continue_execution = False

                    for regexp in allow:

                        if regexp.search(stderr):

                            log.debug(f"Allowing message {regexp.search(stderr)}")
                            continue_execution = True
                            break

                    if continue_execution:

                        continue

                log.debug(f"Error during execution of {cmd}\n\
                ------[STDERR STREAM]------\n\
                {'-'.join(stderr.splitlines(keepends=True))}\n\
                ---------------------------\n")

                fault_simulation_status = FaultSimulation.FSIM_ERROR
                break

            elif stderr == stdout == "TimeoutExpired":

                fault_simulation_status = FaultSimulation.TIMEOUT
                break

        return fault_simulation_status
