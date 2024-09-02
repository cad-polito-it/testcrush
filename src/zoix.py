#!/usr/bin/python3

import sys
import asm
import subprocess
import logging
import re
import enum
import pathlib
import csv

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

class Compilation(enum.Enum):
    ERROR = 0 # stderr contains text
    SUCCESS = 1 # None of the above

class LogicSimulation(enum.Enum):
    TIMEOUT = 0 # Endless loop
    SIM_ERROR = 1 # stderr contains text
    SUCCESS = 2 # None of the above

class LogicSimulationException(BaseException):

    def __init__(self, message = "Error during VC Logic Simulation"):
        self.message = message
        super().__init__(self.message)

class FaultSimulation(enum.Enum):
    TIMEOUT = 0 # Wall-clock
    FSIM_ERROR = 1 # stderr contains text
    SUCCESS = 2 # None of the above

class ZoixInvoker():
    """A wrapper class to be used in handling calls to VCS-Z01X."""
    def __init__(self) -> "ZoixInvoker":
        ...

    @staticmethod
    def execute(instruction : str, timeout : float = None) -> tuple[str, str]:
        """Executes a bash command-string instruction and returns
        the `stdout` and `stderr` responses as a tuple.

        - Parameters:
            - instruction (str): The bash instruction to be executed.
        - Returns:
            - tuple(str, str): The stdout (index 0) and the stderr (index 1) as strings."""

        log.debug(f"Executing {instruction}...")
        try:
            with subprocess.Popen(
                ["/bin/bash", "-c", instruction],
                stdin = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                text = True) as process:

                stdout, stderr = process.communicate(timeout = timeout)

            return stdout, stderr

        except subprocess.TimeoutExpired:

            log.debug(f"TIMEOUT during the execution of:\n\t{instruction}.")
            process.kill()
            return "TimeoutExpired", "TimeoutExpired"

    def compile_sources(self, *instructions : str) -> Compilation:
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

    def logic_simulate(self, *instructions : str, **kwargs) -> LogicSimulation:
        """Performs logic simulation of user-defined firmware and captures the
        test application time
        - Parameters:
            - *instructions (str): A variadic number of bash instructions
            - **kwargs: User-defined options needed for the
            evaluation of the result of the logic simulation. These are:
                - timeout (float): A timeout in **seconds** to be
                used for **each** of the executed lsim instruction.
                - success_regexp (re.regexp): A regular expression which is
                used for matching in every line of the `stdout` stream to
                signify the sucessfull completion of the logic simulation.
                - tat_regexp_capture_group (int): An integer which corresponds
                to the index of the TaT value on the custom regexp (if provided).
                By default is 1, mapping to the default `success_regexp` group.
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

        timeout : float = kwargs.get("timeout", None)

        # The default regexp catches the line:
        # $finish at simulation time  XXXXXXYs
        # where X = a digit and Y = time unit.
        # Capturing of the simulation duration
        # done for possible TaT purposes.
        success : re.regexp = kwargs.get("success_regexp",
            re.compile(r"\$finish[^0-9]+([0-9]+)[m|u|n|p]s", re.DOTALL))

        # By default, a single capturing  group
        # is expected in the regexp, which maps
        # to the TaT value. If a custom  regexp
        # is provided however, with >1  groups,
        # then the user must specify  which  is
        # the expected capture group.
        tat_capture_group : int = kwargs.get("tat_regexp_capture_group", 1)

        # An empty mutable container is expected
        # to store the TaT  value  matched  from
        # the regexp. It is used  like  that  to
        # mimic a pass-by-reference and not alter
        # the function's return value.
        tat_value : list = kwargs.get("tat_value", [])

        simulation_status = None

        for cmd in instructions:

            stdout, stderr = self.execute(cmd, timeout = timeout)

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

                end_reached : re.Match = re.search(success, line)

                if end_reached:

                    test_application_time = end_reached.group(tat_capture_group)
                    try:
                        tat_value.append(int(test_application_time))

                    except ValueError:
                        raise LogicSimulationException(f"Test application time was not correctly captured \
'{test_application_time=}' and could not be converted to an integer. Perhaps there is something wrong with\
your regular expression '{success}' ?")

                    log.debug(f"SIMULATION SUCCESSFULL: {end_reached.groups()}")
                    simulation_status = LogicSimulation.SUCCESS
                    break

        if not simulation_status:
            raise LogicSimulationException(f"Simulation status was not set during \
the execution of {instructions}. Is your regular expression correct? Check the debug log for more information!")

        return simulation_status

    def create_fcm_script(self, fcm_file : pathlib.Path, **fcm_options) -> pathlib.Path:
        """Generates and returns a fault campaign manager TCL script based on
        user-defined settings from the setup file.

        - Parameters:
            - fcm_file (pathlib.Path): The full path (absolute or relative) of the fcm
            script.
            - **fcm_options : Keyword arguments where each key is an fcm command and
            the corresponding value the flags or options (if any). The commands should
            adhere to the supported commands documented in the VCS-Z01X user guide. No
            sanitization checks are performed by the function.

        - Returns:
            - pathlib.Path: The absolute path of the file."""

        log.debug(f"Generating fault campaign manager script {fcm_file.absolute()}.")

        with open(fcm_file, 'w') as fcm_script:

            for command, flags in fcm_options.items():

                fcm_script.write(fr"{command} {flags}" if flags else fr"{command}")
                fcm_script.write("\n")

        return fcm_file.absolute()

    def fault_simulate(self, *instructions : str, **kwargs) -> FaultSimulation:
        """Performs fault simulation of a user-defined firmware.

        - Parameters:
            - *instructions (str): A variadic number of shell instructions
            to invoke Z01X.
            - **kwargs: User-defined options for fault simulation control
                - timeout (float): A timeout in **seconds** for each fsim instruction.
        - Returns:
            - FaultSimulation (enum): A status Enum which is
                - TIMEOUT: if the timeout kwarg was provided and some instruction
                violated it.
                - FSIM_ERROR: if the `stderr` stream contains text during the
                execution of an instruction.
                - SUCCESS: if none of the above.
        """

        fault_simulation_status = FaultSimulation.SUCCESS

        timeout : float = kwargs.get("timeout", None)

        for cmd in instructions:

            stdout, stderr = self.execute(cmd, timeout = timeout)

            if stderr and stderr != "TimeoutExpired":

                log.debug(f"Error during execution of {cmd}\n\
                ------[STDERR STREAM]------\n\
                {'-'.join(stderr.splitlines(keepends = True))}\n\
                ---------------------------\n")

                fault_simulation_status = FaultSimulation.FSIM_ERROR
                break

            elif stderr == stdout == "TimeoutExpired":

                fault_simulation_status = FaultSimulation.TIMEOUT
                break

        return fault_simulation_status

class FaultReport():

    def __init__(self, fault_report : pathlib.Path) -> "FaultReport":
        self.fault_report : pathlib.Path = fault_report.absolute()

    def set_fault_report(self, fault_report : str) -> None:
        """Setter method for fault report.

        - Parameters:
            - fault_report (str): The new fault report filename.

        - Returns:
            - None. Raises FileExistsError if the file does not exist."""

        if not pathlib.Path(fault_report).exists():
            raise FileExistsError(f"Fault report {fault_report} does not exist!")

        self.fault_report = pathlib.Path(fault_report).absolute()

    def extract_fault_report_cells(self, row : int, *cols : int) -> list[str]:
        """Returns a sequence of cells from a row of the CSV fault report.

        - Parameters:
            - row (int): the row number (1-based indexing).
            - *cols (ints): the columns' numbers (1-based indexing).

        - Returns:
            list[str]: The cells of the fault report."""

        with open(self.fault_report) as csv_source:

            reader = csv.reader(csv_source)

            for index, csv_row in enumerate(reader, start = 1):

                if index != row:
                    continue

                try:
                    return [csv_row[col - 1] for col in cols]
                except:
                    raise IndexError(f"A column in {cols} is out of bounds for row {row} of fault report {self.fault_report}.")

            raise IndexError(f"Row {row} is out of bounds for fault report {self.fault_report}.")

def main():

    """Sandbox/Testing Env"""
    A = ZoixInvoker()
    #print(A.logic_simulate("for i in $(seq 100000); do echo $i; done", timeout = 0.1))

    tat_dict = {
        "success_regexp" : re.compile(r"test application time = ([0-9]+)"),
        "tat_regexp_capture_group" : 1,
        "tat_value" : []
    }

    fcm_dict = {
        "set_config" : "-global_max_jobs 64",
        "create_testcases" : '-name {"test1"} -exec ${::env(VCS_WORK_DIR)}/simv -args "./simv +firmware=${::env(FIRMWARE)}" -fsim_args "-fsim=fault+dictionary"',
        "fsim" : "-verbose",
        "report" : "-campaign cv32e40p -report fsim_out.rpt -overwrite",
        "report" : "-campaign cv32e40p -report fsim_out_hier.rpt -overwrite -hierarchical 3"
    }

    res = A.logic_simulate("cat logic_sim_excerpt.log",
        timeout = 60.0,
        **tat_dict)

    A.create_fcm_script(pathlib.Path("fcm.tcl"), **fcm_dict)

    print(tat_dict['tat_value'])
    print(res)

    B = FaultReport("summary.csv.log")
    print(B.extract_csv_cell(16,8))

if __name__ == "__main__":

    main()
