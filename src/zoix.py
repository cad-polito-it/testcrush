#!/usr/bin/python3

import sys
import asm
import subprocess 
import logging 
import re 
import enum

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

class LogicSimulation(enum.Enum):
    TIMEOUT = 0 # Endless loop
    SIM_ERROR = 1 # stderr contains text
    SUCCESS = 2 # None of the above

class LogicSimulationException(BaseException):

    def __init__(self, message = "Error during VC Logic Simulation"):
        self.message = message
        super().__init__(self.message)

class Compilation(enum.Enum):
    ZOIX_ERROR = 0 # stderr contains text
    SUCCESS = 1 # None of the above

class ZoixInvoker():

    def __init__(self, fsim_threads : int) -> 'ZoixInvoker':

        self.coverage : float = 0.0
        self.fsim_threads : int = fsim_threads
    
    @staticmethod
    def execute(instruction : str, timeout : float = None) -> tuple[str, str]:
        """Executes a bash command-string instruction and returns
        the `stdout` and `stderr` responses as a tuple.
        
        - Parameters:
            - instruction (str): The bash instruction to be executed.
        - Returns:
            - tuple(str, str): The stdout (index 0) and the stderr (index 1) string."""

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

    def compile_sources(self, *instructions : str, **kwargs) -> Compilation:
        ... #TODO

    def logic_simulate(self, *instructions : str, **kwargs) -> LogicSimulation:
        """Takes a number of bash instructions which are expected to be either
        bash scripts, or build instructions (e.g., make) to perform a 
        logic simulation of an assembly file using VCS in shell mode
        - Parameters: 
            - *instructions (str): A series of bash shell instructions
            - **kwargs: User-defined options needed for the
            evaluation of the result of the logic simulation. These are:
                - timeout (float): A global timeout to be used for **each**
                of the executed lsim instruction.
                - success_regexp (re.regexp): A regular expression which is
                used for matching in every line of the `stdout` stream to
                signify the sucessfull completion of the logic simulation.
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
        # done for possible TaT purposes. TODO
        success : re.regexp = kwargs.get("success_regexp", 
            re.compile(r"\$finish[^0-9]+([0-9]+)[m|u|n|p]s", re.DOTALL))

        # TODO: Handle all OK/NO_OK scenarios for compilation statuses.

        simulation_status = None

        for cmd in instructions:

            stdout, stderr = self.execute(cmd, timeout = timeout)

            if stderr and stderr != "TimeoutExpired":
                
                log.debug(f"Error during execution of {cmd}\n\
                ---------[MESSAGE]---------\n\
                {'-'.join(stderr.splitlines(keepends=True))}\n\
                ---------------------------\n")

                simulation_status = LogicSimulation.SIM_ERROR                
                break 

            elif stderr == stdout == "TimeoutExpired":
                simulation_status = LogicSimulation.TIMEOUT
                break

            
            for line in stdout.splitlines():
                log.debug(f"{cmd}: {line.rstrip()}")
                
                if re.match(success, line):
                    log.debug(f"SIMULATION SUCCESSFULL: {re.match(success, line).groups()}")
                    simulation_status = LogicSimulation.SUCCESS
                    break

        if not simulation_status:
            raise LogicSimulationException(f"Simulation status was not set during\
            the execution of {instructions}. Check the debug log for more information!")
        
        return simulation_status

def main():
    """Sandbox/Testing Env"""
    A = ZoixInvoker(16)
    #A.logic_simulate("for i in $(seq 100000); do echo $i; done", timeout = 0.1)
    res = A.logic_simulate("cat oksimlog.log", timeout = 60.0)
    print(res)
if __name__ == "__main__":

    main()