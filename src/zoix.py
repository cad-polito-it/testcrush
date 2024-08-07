#!/usr/bin/python3

import sys
import asm
import subprocess 
import logging 
import re 

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

class ZoixInvoker():

    def __init__(self, fsim_threads : int) -> 'ZoixInvoker':

        self.coverage : float = 0.0
        self.fsim_threads : int = fsim_threads
    
    def logic_simulate(self, *instructions : str, **ok_conditions) -> bool:
        """Takes a number of bash instructions which are expected to be either
        bash scripts, or build instructions (e.g., make) to perform a 
        logic simulation of an assembly file using VCS in shell mode
        
        Args: 
            - *instructions (str): A series of bash shell instructions
            - **ok_conditions : ... TODO:
        Returns:
            - bool : True if logic_simulation was successfull. False otherwise."""
        
        timeout : int = ok_conditions.get("timeout", 60)
        success_msg : re.regexp = ok_conditions.get("success_regexp", None)
        finish_msg : re.regexp = ok_conditions.get("finish_regexp", None)
        
        # TODO: Handle all OK/NO_OK scenarios for compilation statuses.

        for cmd in instructions:

            log.debug(f"Executing instruction '{cmd}'.")
            
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
                    return False

                for line in stdout.splitlines():
                    log.debug(f"{cmd}: {line.rstrip()}")
                
                print(stdout)
        
        return True
        
        
def main():

    A = ZoixInvoker(16)
    A.logic_simulate("make vcs/sim/gate/shell --directory ../cv32e40p")

if __name__ == "__main__":

    main()