#!/usr/bin/python3

import pathlib 
import logging
import sys
import re
import random
from dataclasses import dataclass 

@dataclass 
class Codeline:
    """Represents a line of assembly code"""
    lineno : int 
    data : str 
    valid_insn : bool

    def __repr__(self):
        return f"Codeline({self.lineno=}, {self.data}, {self.valid_insn=})"

    def __str__(self):
        return f"[#{self.lineno}]: {self.data}"

    def __isub__(self, other : int):
        
        if not isinstance(other, int):
            raise TypeError(f"Unsupported type for -=: {type(other)}")
        
        if self.lineno > 0:
            self.lineno -= 1
        
        return self
    
    def __iadd__(self, other : int):

        if not isinstance(other, int):
            raise TypeError(f"Unsupported type for +=: {type(other)}")
        
        self.lineno += 1

        return self
    
    def __gt__(self, other : 'Codeline|int') -> bool:
        
        if isinstance(other, int):
            return self.lineno > other
        elif isinstance(other, Codeline):
            return self.lineno > other.lineno
        else:
            raise TypeError(f"Unsupported type for >: {type(other)}")

    def __lt__(self, other : 'Codeline|int') -> bool:
        
        if isinstance(other, int):
            return self.lineno < other
        elif isinstance(other, Codeline):
            return self.lineno < other.lineno
        else:
            raise TypeError(f"Unsupported type for <: {type(other)}")
        
    def __le__(self, other : 'Codeline|int') -> bool:
        
        if isinstance(other, int):
            return self.lineno <= other
        elif isinstance(other, Codeline):
            return self.lineno <= other.lineno
        else:
            raise TypeError(f"Unsupported type for <=: {type(other)}")
    
    def __ge__(self, other : 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno >= other
        elif isinstance(other, Codeline):
            return self.lineno >= other.lineno
        else:
            raise TypeError(f"Unsupported type for >=: {type(other)}")
    
    def __ne__(self, other : 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno != other
        elif isinstance(other, Codeline):
            return self.lineno != other.lineno
        else:
            raise TypeError(f"Unsupported type for !=: {type(other)}")

    def __eq__(self, other : 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno == other
        elif isinstance(other, Codeline):
            return self.lineno == other.lineno
        else:
            raise TypeError(f"Unsupported type for ==: {type(other)}")

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
    """This class  is responsible of managing **one** assembly file. 
    It operates on the `assembly_source` file and removes/restores code lines."""

    def __init__(self, isa : ISA, assembly_source : pathlib.Path, chunksize : int = 1) -> 'AssemblyHandler':
        
        self.isa : ISA = isa
        self.asm_file : pathlib.Path = assembly_source
        self.code : list[Codeline] = list() # 0-based indexing for lineno attribute!
        self.asm_file_changelog : list = list()

        assembly_source = assembly_source.resolve()

        try:
            with open(assembly_source) as asm_file:

                log.debug(f"Reading from file {assembly_source}")

                for lineno, line in enumerate(asm_file, start = 0):
                    
                    # We are currently not interested in the contents
                    # of each line of code. We just want to   extract
                    # the codeline as-is and remove any \s whitespace  
                    line = re.sub(r'\s+', ' ', line.strip())
                    
                    if not line: 
                        continue

                    self.code.append(Codeline(
                        lineno = lineno,
                        data = fr"{line}", 
                        valid_insn = isa.is_instruction(line))
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
    
    def get_candidate(self, lineno : int) -> Codeline:
        """Returns the Codeline in candidates with the specified lineno
        
        Args:
            - lineno (int): the line number of the candidate to be found.
        
        Returns:
            - Codeline : the `Codeline` with `Codeline.lineno == lineno`
        if found. Raises LookupError otherwise."""

        for chunk in self.candidates:

            for codeline in chunk:

                if codeline.lineno == lineno:

                    return codeline 
        
        raise LookupError(f"Requested Codeline with {lineno=} not found!")

    def get_random_candidate(self, pop_candidate = True) -> Codeline:
        """In a uniform random manner selects one `Codeline` and returns it
        while also optionally removing it from the `candidate` collection
        
        Args:
            - pop_candidate (bool): When True, deletes the `Codeline` from the collection
            after identifying it.
             
        Returns:
            - Codeline: A random `Codeline` from a random `self.candidates` chunk."""
        
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

        log.debug(f"Randomly selected {codeline=}")
        return codeline

    def remove(self, codeline : Codeline, replace : bool = False) -> None:
        """Creates a new assembly file by using the current `self.asm_code`
        as a source and skips the  the line which corresponds to `codeline`'s 
        `lineno` attribute.
        
        Args:
            - codeline (Codeline): The `Codeline` to be removed from the
            assembly file.
            - replace (bool): Replaces the old assembly file with the 
            new one if True.
        
        Returns: Nothing"""

        log.debug(f"Removing {codeline}")

        # Appending the line number that is eliminated each time
        # to the filename stem each time.
        new_filename = f"{self.asm_file.parent}/{self.asm_file.stem}_{codeline.lineno}{self.asm_file.suffix}"
        new_asm_file = pathlib.Path(new_filename)

        # Updating changelog to keep track of the edits to the asm file
        self.asm_file_changelog.append(codeline)

        with open(self.asm_file) as source, open(f"{new_asm_file}", 'w') as new_source:

            for lineno, line in enumerate(source, start = 0):

                if codeline == lineno: 
                    
                    log.debug(f"Removing line #{lineno} = {codeline.data}")

                    # Update the lineno attribute of every codeline
                    # that is below the just removed codeline. 
                    for chunk in self.candidates:
                        
                        for chunk_codeline in chunk: 

                            if chunk_codeline > lineno:

                                chunk_codeline -= 1
                                
                    continue
                
                new_source.write(f"{line}")

        log.debug(f"Updating {self.asm_file=} to {new_filename}")
        log.debug(f"Changelog entries are now {self.asm_file_changelog}")

        if replace:
            log.debug(f"Overwritting {self.asm_file} with {new_filename}")
            new_asm_file.replace(str(self.asm_file))
        
        self.asm_file = new_asm_file

        return
        
    def restore(self, replace = False) -> None:
        """Re-enters the last `Codeline` from the changelog to the assembly
        file. The `self.candidates` lineno fields are updated if >= than the 
        entry which is being restored.
        
        Args: 
            - replace (bool): Replaces the old assembly file with the 
            new one if True.
        
        Returns: Nothing"""

        if not self.asm_file_changelog:
            return
        
        # Removing the last segment of the stem of current
        # assembly filename as, we are undoing the  latest
        # change.
        new_filename_stem = "_".join(self.asm_file.stem.split('_')[:-1])
        new_filename = f"{self.asm_file.parent}/{new_filename_stem}{self.asm_file.suffix}"
        new_asm_file = pathlib.Path(new_filename)

        codeline_to_be_restored : Codeline = self.asm_file_changelog.pop()

        log.debug(f"Restoring {codeline_to_be_restored}")

        # The candidates that have a lineno >= to the line
        # to be restored must get a +1 to their lineno at-
        # ribute in order to be aligned with the  original
        # assembly source file line numbers.
        for chunk in self.candidates:
            
            for chunk_codeline in chunk:

                if chunk_codeline >= codeline_to_be_restored:
                    
                    chunk_codeline += 1
        
        with open(self.asm_file) as source, open(new_asm_file, 'w') as new_source:

            for lineno, line in enumerate(source, start = 0):

                if codeline_to_be_restored != lineno:
                    
                    new_source.write(line)
                
                else:
                
                    log.debug(f"Re-inserting line#{lineno} to assembly source.")
                    new_source.write(f"{codeline_to_be_restored.data}\n")
        
        log.debug(f"Updating {self.asm_file=} to {new_asm_file}")
        log.debug(f"Changelog entries are now {self.asm_file_changelog}")

        if replace:
            log.debug(f"Overwritting {self.asm_file} with {new_filename}")
            new_asm_file.replace(str(self.asm_file))

        self.asm_file = new_asm_file

        return

def main():
    """Sandbox/Testing Env"""
    C = ISA(pathlib.Path("../langs/riscv.isa"))
    A = AssemblyHandler(C, pathlib.Path("../sandbox/sbst_01/src/tests/test1.S"), chunksize = 2)
    random_candidate = A.get_random_candidate()
    A.remove(random_candidate)
    A.restore()

if __name__ == "__main__":

    log = logging.getLogger("SQUEEZER_LOGGER")
    log.setLevel(logging.DEBUG)
    log_stream = logging.StreamHandler(stream = sys.stdout)
    log_stream.setLevel(logging.INFO)
    log_stream.setFormatter(logging.Formatter('[%(levelname)s]: %(message)s'))
    log_file = logging.FileHandler(filename = "debug.log", mode = 'w')
    log_file.setLevel(logging.DEBUG)
    log_file.setFormatter(logging.Formatter('[%(levelname)s|%(module)s|%(funcName)s]: %(message)s'))
    log.addHandler(log_stream)
    log.addHandler(log_file)

    main()
