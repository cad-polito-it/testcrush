import pathlib 
import logging
import sys 

class Singleton(type):
    
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        
        if cls not in cls._instances:
            
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance

        return cls._instances[cls]
    
class AssemblyParser(metaclass = Singleton):
    
    def __init__(self, isa : pathlib.Path):
        
        self.keywords : set = set()
        with open(isa) as isa_keywords:

            log.debug(f"Reading from file {isa}")
            lines = [ x.rstrip() for x in isa_keywords.readlines() ]

        for lineno, line in enumerate(lines, start = 1):

            # Simple sanity check 
            if line[0] != '#' and len(line.split()) > 1:

                log.fatal(f"Wrong syntax at line {lineno} of {isa} file")
                exit(1)

            # Skip comment lines 
            if line[0] == '#': 
                continue
            
            self.keywords.add(line)
      
    def is_instruction(self, assembly_line : str) -> bool:
        """Checks if `assembly_line` is present the class `keywords` set.

        Args:
            assembly_line (str): an assembly mnemonic

        Returns:
            bool: True if `assembly_line` is in `keywords`, False otherwise.
        """
        if assembly_line.lstrip().split()[0] in self.keywords:
            return True

        return False

def main():

    A = AssemblyParser("../langs/riscv.isa")
    print(A.is_instruction("add"))

if __name__ == "__main__":

    log = logging.getLogger("SQUEEZER_LOGGER")
    log.setLevel(logging.INFO)
    log_stream = logging.StreamHandler(stream = sys.stdout)
    log_stream.setLevel(logging.INFO)
    log_stream.setFormatter(logging.Formatter('[%(levelname)s]: %(message)s'))
    log_file = logging.FileHandler(filename = "debug.log")
    log_file.setLevel(logging.DEBUG)
    log_file.setFormatter(logging.Formatter('[%(levelname)s|%(module)s]: %(message)s'))
    log.addHandler(log_stream)
    log.addHandler(log_file)

    main()
