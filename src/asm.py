#!/usr/bin/python3

import pathlib 
import logging
import sys
import re
import random
from collections import namedtuple

Codeline = namedtuple("Codeline", ['lineno', 'data', 'valid_insn'])

class Singleton(type):
    
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        
        if cls not in cls._instances:

            log.debug(f"Singleton {cls.__name__} created!")
            
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance

        return cls._instances[cls]

class ISA(metaclass = Singleton):
    """This **Singleton** class provides utilities for the considered ISA."""

    def __init__(self, isa : pathlib.Path) -> "ISA":

        self.mnemonics : set = set()
        self.source: pathlib.Path = str()

        try: 
            with open(isa) as isa_keywords:

                log.debug(f"Reading ISA language from file {isa.resolve()}")
                lines = [ x.rstrip() for x in isa_keywords.readlines() ]
        
        except FileNotFoundError:
            log.fatal(f"ISA File {isa} not found! Exiting...")
            exit(1)

        for lineno, line in enumerate(lines, start = 1):

            # Simple sanity check 
            if line[0] != '#' and len(line.split()) > 1:

                log.fatal(f"Wrong syntax at line {lineno} of {isa} file")
                exit(1)

            # Skip comment lines 
            if line[0] == '#': 
                continue
            
            self.mnemonics.add(line)

    def __repr__(self):
        return f"ISA('{str(self.source)})"
    
    def get_mnemonics(self) -> set:
        """Returns a set with the ISA-lang mnemonics.
        
        Args:
        
        Returns:
            - set: A set with all the ISA-lang mnemonics."""
        return self.mnemonics

    def is_instruction(self, assembly_line : str) -> bool:
        """Checks if `assembly_line`'s first sub-string is present the class `keywords` set.

        Args:
            - assembly_line (str): an assembly mnemonic.

        Returns:
            - bool: True if `assembly_line` is in `mnemonics`, False otherwise.
        """
        potential_instruction = assembly_line.split()[0]
        return potential_instruction in self.mnemonics
    
class AssemblyHandler():
    """This class inherits from the Singleton `ISA` class and is responsible
    for managing **one** assembly file. It operates on the `assembly_source`
    file and removes/restores code lines."""

    def __init__(self, isa : ISA, assembly_source : pathlib.Path, chunksize = 1) -> 'AssemblyHandler':
        
        self.isa : ISA = isa
        self.asm_file : pathlib.Path = assembly_source
        self.code : list[Codeline] = list() # 0-based indexing for lineno attribute!
        self.asm_file_changelog : set = set()

        assembly_source = assembly_source.resolve()

        try:
            with open(assembly_source) as asm_file:

                log.debug(f"Reading from file {assembly_source}")

                for lineno, line in enumerate(asm_file, start=0):
                    
                    # We are currently not interested in the contents
                    # of each line of code. We just want to   extract
                    # the codeline as-is and remove any \s whitespace  
                    line = re.sub(r'\s+', ' ', line.strip())
                    
                    if not line: 
                        continue

                    self.code.append(Codeline(
                        lineno = lineno,
                        data = line, 
                        valid_insn = True if isa.is_instruction(line) else False)
                    )

        except FileNotFoundError:
        
            log.fatal(f"Assembly source file {assembly_source} not found! Exiting...")
            exit(1)
        
        self.candidates = [codeline for codeline in self.code if codeline.valid_insn]
        self.candidates = [self.candidates[i:i + chunksize] for i in range(0, len(self.candidates), chunksize)]

    def get_asm_source(self) -> pathlib.Path:
        """Returns the assembly source file `pathlib.Path`.
        
        Args:
            
        Returns:
            - pathlib.Path: The assembly source `pathlib.Path`."""
        return self.asm_file

    def get_code(self) -> list[Codeline]:
        """Returns the parsed code as a list of `Codelines`.
        
        Args:
        
        Returns:
            - list: A list of `Codeline` entries."""
        return self.code

    def get_random_candidate(self, pop_candidate = True) -> Codeline:
        """In a uniform random manner selects one `Codeline` and returns it
        while also optionally removing it from the `candidate` collection
        
        Args:
            - pop_candidate (bool): When True, deletes the `Codeline` from the collection
            after identifying it.
             
        Returns:
            - Codeline: A random `Codeline` from a random chunk."""
        random_chunk = random.randint(0, len(self.candidates) - 1)            
        random_codeline = random.randint(0, len(self.candidates[random_chunk]) - 1)      

        # Check if it's the last codeline of the chunk
        # and delete the chunk after popping it.
        if pop_candidate:
            codeline = self.candidates[random_chunk].pop(random_codeline)
            if not self.candidates[random_chunk]:
                del self.candidates[random_chunk]
        else:
            codeline = self.candidates[random_chunk][random_codeline]

        return codeline

    def remove_from_source(self, codeline : Codeline) -> None:
        """Modifies the corresponding assembly file (source) by removing 
        the line which corresponds to `codeline`'s `lineno` attribute."""
        print("Todo!")

def main():
    C = ISA(pathlib.Path("../langs/riscv.isa"))
    A = AssemblyHandler(C, pathlib.Path("../sandbox/sbst_01/src/tests/test1.S"),chunksize=2)
    cands = A.get_random_candidate()

    print(cands)
    #print(cands)

if __name__ == "__main__":

    log = logging.getLogger("SQUEEZER_LOGGER")
    log.setLevel(logging.DEBUG)
    log_stream = logging.StreamHandler(stream = sys.stdout)
    log_stream.setLevel(logging.INFO)
    log_stream.setFormatter(logging.Formatter('[%(levelname)s]: %(message)s'))
    log_file = logging.FileHandler(filename = "debug.log")
    log_file.setLevel(logging.DEBUG)
    log_file.setFormatter(logging.Formatter('[%(levelname)s|%(module)s|%(funcName)s]: %(message)s'))
    log.addHandler(log_stream)
    log.addHandler(log_file)

    main()
