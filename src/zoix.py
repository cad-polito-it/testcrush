#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import sys
import subprocess
import logging
import re
import enum
import pathlib
import csv

# TEMPORARY
log = logging.getLogger("testcrush logger")
log.setLevel(logging.DEBUG)
log_stream = logging.StreamHandler(stream=sys.stdout)
log_stream.setLevel(logging.INFO)
log_stream.setFormatter(logging.Formatter('[%(levelname)s]: %(message)s'))
log_file = logging.FileHandler(filename="debug.log", mode='w')
log_file.setLevel(logging.DEBUG)
log_file.setFormatter(logging.Formatter(
    '%(lineno)d:[%(levelname)s|%(module)s|%(funcName)s]: %(message)s'))
log.addHandler(log_stream)
log.addHandler(log_file)


class Compilation(enum.Enum):

    ERROR = 0  # stderr contains text
    SUCCESS = 1  # None of the above


class LogicSimulation(enum.Enum):

    TIMEOUT = 0  # Endless loop
    SIM_ERROR = 1  # stderr contains text
    SUCCESS = 2  # None of the above


class LogicSimulationException(BaseException):

    def __init__(self, message="Error during VC Logic Simulation"):
        self.message = message
        super().__init__(self.message)


class FaultSimulation(enum.Enum):

    TIMEOUT = 0  # Wall-clock
    FSIM_ERROR = 1  # stderr contains text
    SUCCESS = 2  # None of the above


class Fault():
    """Generic representation of a fault.
    All attributes are set as strings"""

    def __init__(self, **fault_attributes: dict[str, str]) -> 'Fault':
        for attribute, value in fault_attributes.items():
            setattr(self, attribute.replace(" ", "_"), value)

    def __repr__(self):
        attrs = ', '.join(f'{key}={value!r}' for key, value in
                          self.__dict__.items())
        return f'{self.__class__.__name__}({attrs})'

    def __str__(self):
        return ', '.join(f'{key}: {value}' for key, value in
                         self.__dict__.items())

    def __eq__(self, other):

        if isinstance(other, Fault):
            return self.__dict__ == other.__dict__

        return False

    def get(self, attribute: str, default: str | None = None) -> str:
        """Generic getter method."""
        return getattr(self, attribute.replace(" ", "_"), default)

    def cast_attribute(self, attribute: str, func: callable) -> None:
        """Casts the type of the internal attribute"""
        attribute = attribute.replace(" ", "_")
        try:
            self.__dict__[attribute] = func(getattr(self, attribute))

        except KeyError:
            log.error(f"Attribute {attribute} not a \
member of {self.__class__}")

        except ValueError:
            log.critical(f"Unable to perform the cast operation to \
{repr(func)} of attribute {getattr(self, attribute)}")
            exit(1)


class CSVFaultReport():
    """Manipulates the VC-Z01X summary and report **CSV** files which are
    generated after fault simulation. The `report` instruction specified in the
    `fcm.tcl` file **MUST** be executed with the `-csv` option."""

    def __init__(self, fault_summary: pathlib.Path,
                 fault_report: pathlib.Path) -> "CSVFaultReport":

        self.fault_summary: pathlib.Path = fault_summary.absolute()
        self.fault_report: pathlib.Path = fault_report.absolute()

    def set_fault_summary(self, fault_summary: str) -> None:
        """Setter method for fault summary.

        - Parameters:
            - fault_summary (str): The new fault summary filename.

        - Returns:
            - None. Raises FileExistsError if the file does not exist."""

        if not pathlib.Path(fault_summary).exists():
            raise FileExistsError(f"{fault_summary=} does not exist!")

        self.fault_summary = pathlib.Path(fault_summary).absolute()

    def set_fault_report(self, fault_report: str) -> None:
        """Setter method for fault report.

        - Parameters:
            - fault_report (str): The new fault report filename.

        - Returns:
            - None. Raises FileExistsError if the file does not exist."""

        if not pathlib.Path(fault_report).exists():
            raise FileExistsError(f"{fault_report=} does not exist!")

        self.fault_report = pathlib.Path(fault_report).absolute()

    def extract_summary_cells_from_row(self,
                                       row: int,
                                       *cols: int) -> list[str]:
        """Returns a sequence of cells from a row of the
        `self.fault_summary` **CSV** file.

        - Parameters:
            - row (int): the row number (1-based indexing).
            - *cols (ints): the columns' numbers (1-based indexing).

        - Returns:
            - list[str]: The cells of the fault summary."""

        with open(self.fault_summary) as csv_source:

            reader = csv.reader(csv_source)

            for index, csv_row in enumerate(reader, start=1):

                if index != row:
                    continue

                try:
                    return [csv_row[col - 1] for col in cols]
                except IndexError:
                    log.critical(f"A column in {cols} is out of bounds \
for row {row} of fault summary {self.fault_summary}.")
                    exit(1)

            log.critical(f"Row {row} is out of bounds \
for fault summary {self.fault_summary}.")
            exit(1)

    def parse_fault_report(self) -> list[Fault]:
        """Parses the `self.fault_report` **CSV** file and returns a dictionary
        with its contents, ommiting any column if specified.

        - Parameters:
            - None:

        - Returns:
            - list[Fault]: A list with synopys fault format objects.
        """

        with open(self.fault_report) as csv_source:

            reader = csv.reader(csv_source)

            # Attributes
            attributes = next(reader)

            return [Fault(**dict(zip(attributes, csv_row))) for csv_row
                    in reader]

    @staticmethod
    def compute_flist_coverage(fault_list: list[Fault],
                               sff_file: pathlib.Path,
                               formula: str,
                               precision: int = 4,
                               status_attribute: str = "Status") -> float:
        """Computes the test coverage percentage as described by `formula`,
        which must be comprised of mathematical operations of Z01X fault
        classes (i.e., 2 letter strings).

        - Parameters:
            - fault_list (list(Fault)): A fault-list generated after parsing
            the Z01X fault report csv file.
            - sff_file (pathlib.Path): The fault format configuration file.
            - formula (str): A formula which computes the coverage e.g.,
            `"DD/(NA + DA + DN + DD)"`.
            - precision (int): the number of decimals to consider for
            the coverage. Default is `4`.
            - status_attribute (str): The attribute of the `Fault` object
            which represents its Z01X fault status/class. Default is "Status".
        - Returns:
            float: The coverage percentage i.e., the evaluated `formula`."""

        # Gather fault statuses numbers.
        fault_statuses = dict()

        for fault in fault_list:

            status = fault.get(status_attribute)
            if status in fault_statuses:
                fault_statuses[status] += 1
            else:
                fault_statuses[status] = 1

        # Parse StatusGroups section.
        with open(sff_file) as config:

            try:
                status_groups_raw = re.search(
                    r"StatusGroups\n\s*{([^}]+)\s*}",
                    config.read(),
                    re.MULTILINE).group(1).splitlines()

            except AttributeError:
                log.critical(f"Unable to extract StatusGroups segment \
from the {sff_file}. Exiting...")
                exit(1)

        # Remove empty lines if any.
        status_groups_raw = list(filter(lambda x: len(x),
                                        map(str.strip, status_groups_raw)))
        status_groups = dict()

        for line in status_groups_raw:

            group, *statuses = re.findall(r"([A-Z]{2})", line)

            status_groups[group] = 0

            for status in statuses:
                if status in fault_statuses:
                    status_groups[group] += fault_statuses[status]

        # Finally get any group only present
        # in the formula and set it to 0.
        non_present_statuses = dict()

        for status in re.findall(r"[A-Z]{2}", formula):

            if status not in fault_statuses.keys() and \
               status not in status_groups.keys():
                non_present_statuses[status] = 0

        return round(eval(formula,
                          {
                            **fault_statuses,
                            **status_groups,
                            **non_present_statuses
                          }),
                     precision)


class ZoixInvoker():
    """A wrapper class to be used in handling calls to VCS-Z01X."""
    def __init__(self) -> "ZoixInvoker":
        ...

    @staticmethod
    def execute(instruction: str, timeout: float = None) -> tuple[str, str]:
        """Executes a bash command-string instruction and returns
        the `stdout` and `stderr` responses as a tuple.

        - Parameters:
            - instruction (str): The bash instruction to be executed.
        - Returns:
            - tuple(str, str): The stdout (index 0) and the stderr (index 1)
            as strings."""

        log.debug(f"Executing {instruction}...")
        try:
            with subprocess.Popen(
              ["/bin/bash", "-c", instruction],
              stdin=subprocess.PIPE,
              stdout=subprocess.PIPE,
              stderr=subprocess.PIPE,
              text=True) as process:

                stdout, stderr = process.communicate(timeout=timeout)

            return stdout, stderr

        except subprocess.TimeoutExpired:

            log.debug(f"TIMEOUT during the execution of:\n\t{instruction}.")
            process.kill()
            return "TimeoutExpired", "TimeoutExpired"

    def compile_sources(self, *instructions: str) -> Compilation:
        """Performs compilation of HDL files

        - Parameters:
            - *instructions (str): A variadic number of bash shell instructions

        Returns:
            - Compilation: A status Enum to signify the success or failure
            of the compilation.
        """

        compilation_status = Compilation.SUCCESS

        for cmd in instructions:

            stdout, stderr = self.execute(cmd)

            if stderr:

                compilation_status = Compilation.ERROR
                break

        return compilation_status

    def logic_simulate(self, *instructions: str, **kwargs) -> LogicSimulation:
        """Performs logic simulation of user-defined firmware and captures the
        test application time
        - Parameters:
            - *instructions (str): A variadic number of bash instructions
            - **kwargs: User-defined options needed for the
            evaluation of the result of the logic simulation. These are:
                - timeout (float): A timeout in **seconds** to be
                used for **each** of the executed lsim instruction.
                - success_regexp (re.Pattern): A regular expression which is
                used for matching in every line of the `stdout` stream to
                signify the sucessfull completion of the logic simulation.
                - tat_regexp_capture_group (int): An integer which corresponds
                to the index of the TaT value on the custom regexp
                (if provided). By default is 1, mapping to the default
                `success_regexp` group.
                - tat_value (list): An **empty** list to store the value of the
                tat after being successfully matched with `success_regexp`.
                Pass-by-reference style.
        - Returns:
            - LogicSimulation (enum):
                - TIMEOUT: if user defined timeout has been triggered.
                - SIM_ERROR: if any text was found in the `stderr` stream
                during the execution of an instruction.
                - SUCCESS: if the halting regexp matched text from the
               `stdout` stream."""

        timeout: float = kwargs.get("timeout", None)

        # The default regexp catches the line:
        # $finish at simulation time  XXXXXXYs
        # where X = a digit and Y = time unit.
        # Capturing of the simulation duration
        # done for possible TaT purposes.
        default_regexp = re.compile(r"\$finish[^0-9]+([0-9]+)[m|u|n|p]s",
                                    re.DOTALL)
        success: re.Pattern = kwargs.get("success_regexp", default_regexp)

        # By default, a single capturing  group
        # is expected in the regexp, which maps
        # to the TaT value. If a custom  regexp
        # is provided however, with >1  groups,
        # then the user must specify  which  is
        # the expected capture group.
        tat_capture_group: int = kwargs.get("tat_regexp_capture_group", 1)

        # An empty mutable container is expected
        # to store the TaT  value  matched  from
        # the regexp. It is used  like  that  to
        # mimic a pass-by-reference and not alter
        # the function's return value.
        tat_value: list = kwargs.get("tat_value", [])

        simulation_status = None

        for cmd in instructions:

            stdout, stderr = self.execute(cmd, timeout=timeout)

            if stderr and stderr != "TimeoutExpired":

                log.debug(f"Error during execution of {cmd}\n\
                ------[STDERR STREAM]------\n\
                {'-'.join(stderr.splitlines(keepends = True))}\n\
                ---------------------------\n")

                simulation_status = LogicSimulation.SIM_ERROR
                break

            elif stderr == stdout == "TimeoutExpired":

                simulation_status = LogicSimulation.TIMEOUT
                break

            for line in stdout.splitlines():

                log.debug(f"{cmd}: {line.rstrip()}")

                end_reached: re.Match = re.search(success, line)

                if end_reached:

                    test_application_time = end_reached.\
                        group(tat_capture_group)
                    try:
                        tat_value.append(int(test_application_time))

                    except ValueError:
                        raise LogicSimulationException(f"Test application \
time was not correctly captured {test_application_time=} and could not be \
converted to an integer. Perhaps there is something wrong with your regular \
expression '{success}' ?")

                    log.debug(f"Simulation SUCCESS: {end_reached.groups()}")
                    simulation_status = LogicSimulation.SUCCESS
                    break

        if not simulation_status:
            raise LogicSimulationException(f"Simulation status was not set \
during the execution of {instructions}. Is your regular expression correct? \
Check the debug log for more information!")

        return simulation_status

    def create_fcm_script(self,
                          fcm_file: pathlib.Path,
                          **fcm_options) -> pathlib.Path:
        """Generates and returns a fault campaign manager TCL script based on
        user-defined settings from the setup file.

        - Parameters:
            - fcm_file (pathlib.Path): The full path (absolute or relative) \
            of the fcm script.
            - **fcm_options: Keyword arguments where each key is an fcm \
            command and the corresponding value the flags or options (if any).\
             The commands should adhere to the supported commands documented \
            in the VCS-Z01X user guide. No sanitization checks are performed \
            by the method.

        - Returns:
            - pathlib.Path: The absolute path of the file."""

        log.debug(f"Generating fault campaign manager script \
{fcm_file.absolute()}.")

        with open(fcm_file, 'w') as fcm_script:

            for command, flags in fcm_options.items():

                fcm_script.write(fr"{command} {flags}" if flags else
                                 fr"{command}")
                fcm_script.write("\n")

        return fcm_file.absolute()

    def fault_simulate(self, *instructions: str, **kwargs) -> FaultSimulation:
        """Performs fault simulation of a user-defined firmware.

        - Parameters:
            - *instructions (str): A variadic number of shell instructions
            to invoke Z01X.
            - **kwargs: User-defined options for fault simulation control
                - timeout (float): A timeout in **seconds** for each fsim
                instruction.
        - Returns:
            - FaultSimulation (enum): A status Enum which is
                - TIMEOUT: if the timeout kwarg was provided and some
                instruction iolated it.
                - FSIM_ERROR: if the `stderr` stream contains text during the
                execution of an instruction.
                - SUCCESS: if none of the above.
        """

        fault_simulation_status = FaultSimulation.SUCCESS

        timeout: float = kwargs.get("timeout", None)

        for cmd in instructions:

            stdout, stderr = self.execute(cmd, timeout=timeout)

            if stderr and stderr != "TimeoutExpired":

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
