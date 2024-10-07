#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import pathlib
import re
import tempfile
import random
import shutil

from testcrush.utils import Singleton, get_logger
from dataclasses import dataclass

log = get_logger()


@dataclass
class Codeline:
    """Represents a line of assembly code"""

    lineno: int
    data: str
    valid_insn: bool

    def __repr__(self):
        return f"Codeline({self.lineno}, \"{self.data}\", valid_insn = {self.valid_insn})"

    def __str__(self):
        return f"[#{self.lineno}]: {self.data}"

    def __isub__(self, other: int):

        if not isinstance(other, int):
            raise TypeError(f"Unsupported type for -=: {type(other)}")

        if self.lineno > 0:
            self.lineno -= other

        return self

    def __iadd__(self, other: int):

        if not isinstance(other, int):
            raise TypeError(f"Unsupported type for +=: {type(other)}")

        self.lineno += other

        return self

    def __gt__(self, other: 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno > other
        elif isinstance(other, Codeline):
            return self.lineno > other.lineno
        else:
            raise TypeError(f"Unsupported type for >: {type(other)}")

    def __lt__(self, other: 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno < other
        elif isinstance(other, Codeline):
            return self.lineno < other.lineno
        else:
            raise TypeError(f"Unsupported type for <: {type(other)}")

    def __le__(self, other: 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno <= other
        elif isinstance(other, Codeline):
            return self.lineno <= other.lineno
        else:
            raise TypeError(f"Unsupported type for <=: {type(other)}")

    def __ge__(self, other: 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno >= other
        elif isinstance(other, Codeline):
            return self.lineno >= other.lineno
        else:
            raise TypeError(f"Unsupported type for >=: {type(other)}")

    def __ne__(self, other: 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno != other
        elif isinstance(other, Codeline):
            return self.lineno != other.lineno
        else:
            raise TypeError(f"Unsupported type for !=: {type(other)}")

    def __eq__(self, other: 'Codeline|int') -> bool:

        if isinstance(other, int):
            return self.lineno == other
        elif isinstance(other, Codeline):
            return self.lineno == other.lineno
        else:
            raise TypeError(f"Unsupported type for ==: {type(other)}")


class ISA(metaclass=Singleton):
    """**Singleton** class to provide utilities for the considered ISA."""

    def __init__(self, isa: pathlib.Path) -> "ISA":

        self.mnemonics: set = set()
        self.source: pathlib.Path = isa.resolve()

        try:
            with open(self.source) as isa_keywords:

                log.debug(f"Reading ISA language from file {self.source}")
                lines = [x.rstrip() for x in isa_keywords.readlines()]

        except FileNotFoundError:
            log.fatal(f"ISA File {self.source} not found! Exiting...")
            exit(1)

        for lineno, line in enumerate(lines, start=1):

            if not line:
                raise SyntaxError(f"Empty line at line number {lineno} of {self.source} file")

            # Simple sanity check
            if line[0] != '#' and len(line.split()) > 1:

                raise SyntaxError(f"Wrong syntax at line {lineno} of {self.source} file")

            # Skip comment lines
            if line[0] == '#':
                continue

            self.mnemonics.add(line.strip())

    def __repr__(self):
        return f"ISA({str(self.source)})"

    def get_mnemonics(self) -> set:
        """
        Returns a set with the ISA-lang mnemonics.

        Args:
            None

        Returns:
            set: A set with all the ISA-lang mnemonics."""

        return self.mnemonics

    def is_instruction(self, assembly_line: str) -> bool:
        """
        Checks if ``assembly_line``'s first sub-string is present the class ``keywords`` set.

        Args:
            assembly_line (str): an assembly mnemonic.

        Returns:
            bool: True if ``assembly_line`` is in ``mnemonics``, False otherwise.
        """

        potential_instruction = assembly_line.split()[0]
        return potential_instruction in self.mnemonics


class AssemblyHandler():
    """
    Manages **one** assembly file.

    It operates on the file by removing/restoring lines of code.
    """

    def __init__(self,
                 isa: ISA,
                 assembly_source: pathlib.Path,
                 chunksize: int = 1) -> 'AssemblyHandler':

        self.isa: ISA = isa
        self.asm_file: pathlib.Path = assembly_source.resolve()
        self.asm_file_changelog: list = list()
        self.candidates: list[list[Codeline]] = list()  # only instructions!

        assembly_source = assembly_source.resolve()

        try:
            code = list()
            with open(assembly_source) as asm_file:

                log.debug(f"Reading from file {assembly_source}")

                # 0-based indexing for lineno!
                for lineno, line in enumerate(asm_file, start=0):

                    # We are currently not interested in the contents
                    # of each line of code. We just want to   extract
                    # the codeline as-is and remove any \s whitespace
                    line = re.sub(r'\s+', ' ', line.strip())

                    if not line:
                        continue

                    code.append(Codeline(
                        lineno=lineno,
                        data=fr"{line}",
                        valid_insn=isa.is_instruction(line)))

        except FileNotFoundError:

            log.fatal(f"Assembly source file {assembly_source} not found! \
Exiting...")
            exit(1)

        self.candidates = [codeline for codeline in code if
                           codeline.valid_insn]
        self.candidates = [self.candidates[i:i + chunksize]
                           for i in range(0, len(self.candidates), chunksize)]

    def get_asm_source(self) -> pathlib.Path:
        """
        Returns the assembly source file ``pathlib.Path``.

        Returns:
            pathlib.Path: The assembly source ``pathlib.Path``.
        """

        return self.asm_file

    def get_code(self) -> list[Codeline]:
        """
        Returns the parsed code as a list of ``Codelines``.

        Returns:
            list: A list of ``Codeline`` entries.
        """

        return [codeline for chunk in self.candidates for codeline in chunk]

    def get_candidate(self, lineno: int) -> Codeline:
        """
        Returns the Codeline in candidates with the specified lineno

        Args:
            lineno (int): the line number of the candidate to be found.

        Returns:
            Codeline: the ``Codeline`` with ``Codeline.lineno == lineno`` if found.

        Raises:
            LookUpError: If the requested Codeline does not exist
        """

        for chunk in self.candidates:

            for codeline in chunk:

                if codeline.lineno == lineno:

                    return codeline

        raise LookupError(f"Requested Codeline with {lineno=} not found!")

    def get_random_candidate(self, pop_candidate: bool = True) -> Codeline:
        """
        In a uniform random manner selects one ``Codeline`` and returns it while also optionally removing it from
        the ``candidate`` collection.

        Args:
            pop_candidate (bool): When True, deletes the ``Codeline`` from the collection after identifying it.

        Returns:
            Codeline: A random ``Codeline`` from a random ``self.candidates`` chunk.
        """

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

    def remove(self, codeline: Codeline) -> None:
        """
        Removes the codeline from the assembly file.

        Creates a new assembly file by using the current ``self.asm_code`` as a source and skips the the line which
        corresponds to ``codeline``'s ``lineno`` attribute. The ``self.candidates`` lineno fields are updated (-1)
        if >= than the entry which is being restored.

        Args:
            codeline (Codeline): The ``Codeline`` to be removed from the assembly file.

        Returns:
            None
        """

        with open(self.asm_file) as source, tempfile.NamedTemporaryFile('w', delete=False) as new_source:

            for lineno, line in enumerate(source, start=0):

                if codeline == lineno:

                    log.debug(f"Removing line #{lineno} = {codeline.data}")

                    continue

                new_source.write(f"{line}")

            new_source.flush()
            new_file = pathlib.Path(new_source.name)
            shutil.move(new_file, self.asm_file)

        # Update the lineno attribute of every codeline
        # that is below the just removed codeline.
        for chunk in self.candidates:

            for chunk_codeline in chunk:

                if chunk_codeline > codeline.lineno:

                    chunk_codeline -= 1

        # Updating changelog to keep track of the edits to the asm file
        self.asm_file_changelog.append(codeline)
        log.debug(f"Changelog entries are now {self.asm_file_changelog}")

    def restore(self) -> None:
        """
        Re-enters the last ``Codeline`` from the changelog to the assembly file.

        The ``self.candidates`` lineno fields are updated (+1) if >= than the entry which is being restored.

        Returns:
            None
        """

        if not self.asm_file_changelog:
            log.debug(f"{self.asm_file_changelog=}  empty, nothing to restore")
            return

        codeline_to_be_restored: Codeline = self.asm_file_changelog.pop()
        log.debug(f"Restoring {codeline_to_be_restored}")

        # The candidates that have a lineno >= to the line
        # to be restored must get a +1 to their lineno at-
        # ribute in order to be aligned with the  original
        # assembly source file line numbers.
        for chunk in self.candidates:

            for chunk_codeline in chunk:

                # If codeline is not removed from the self.candidates
                # then be careful not to modify it. Skip it as it 'll
                # not affect the rest of the code. Otherwise    there
                # will be an off-by-one error on the insertion point.
                if chunk_codeline is codeline_to_be_restored:

                    continue

                if chunk_codeline >= codeline_to_be_restored:

                    chunk_codeline += 1

        with open(self.asm_file) as source, tempfile.NamedTemporaryFile('w', delete=False) as new_source:

            line_restored = False
            for lineno, line in enumerate(source, start=0):

                if codeline_to_be_restored == lineno:
                    new_source.write(f"{codeline_to_be_restored.data}\n")
                    line_restored = True

                new_source.write(line)

            if not line_restored:  # its the very last line
                new_source.write(f"{codeline_to_be_restored.data}\n")

            log.debug(f"Changelog entries are now {self.asm_file_changelog}")

            new_source.flush()
            new_file = pathlib.Path(new_source.name)
            shutil.move(new_file, self.asm_file)

    def save(self) -> str | None:
        """
        Saves the current version of assembly file. The filename will be the original stem plus all current changelog
        codelines' linenos seperated with a dash. If ``self.asm_file_changelog`` is empty, it does nothing.

        Returns:
            str: The filename (path) of the saved file.
        """

        if not self.asm_file_changelog:
            log.debug("No changes in changelog to be saved.")
            return

        filename = self.asm_file.parent / pathlib.Path(f"{self.asm_file.stem}-"
                                                       + '-'.join([str(codeline.lineno) for
                                                                   codeline in self.asm_file_changelog])
                                                       + f"{self.asm_file.suffix}")

        shutil.copy(self.asm_file, filename)
