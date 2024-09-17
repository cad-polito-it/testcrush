#!/usr/bin/python3

from testcrush import asm, utils

import unittest
import unittest.mock as mock

import pathlib
import os
import copy
import shutil
import random
import sys
class CodelineTest(unittest.TestCase):

    @staticmethod
    def gen_codeline_obj(lineno : int, data : str = "Dummy Text", valid_insn : bool = True):
        return asm.Codeline(lineno, data, valid_insn)

    def test_repr(self):

        random_int = random.randint(0, sys.maxsize)
        test_obj = self.gen_codeline_obj(random_int)
        self.assertEqual(repr(test_obj), f"Codeline({random_int}, \"Dummy Text\", valid_insn = True)")

    def test_str(self):

        random_int = random.randint(0, sys.maxsize)
        test_obj = self.gen_codeline_obj(random_int)
        self.assertEqual(str(test_obj), f"[#{random_int}]: Dummy Text")

    def test_isub_when_lineno_is_zero(self):
        """
        If a Codeline object has a lineno attribute set to 0
        then the -=1 should not modify it.
        """

        test_obj = self.gen_codeline_obj(0)
        test_obj -= 1
        self.assertEqual(test_obj.lineno, 0)

    def test_isub_when_lineno_is_ge_zero(self):
        """
        The Codeline's lineno attribute shall be reduced by 1.
        """
        random_non_zero_int = random.randint(1, sys.maxsize)
        test_obj = self.gen_codeline_obj(random_non_zero_int)
        test_obj -= 1
        self.assertEqual(test_obj.lineno, random_non_zero_int - 1)

    def test_isub_for_chunks_of_codelines(self):

        # Test similar to struct appearing in the asm.py code for modifying codelines in candidates
        test_objs = [ [self.gen_codeline_obj(i), self.gen_codeline_obj(i+1) ] for i in range(1,100,2) ]
        line_numbers = [ [x.lineno, y.lineno ] for chunk_codeline in test_objs for x, y in [chunk_codeline] ]

        for chunk in test_objs:
            for chunk_codeline in chunk:
                chunk_codeline -= 1

        new_line_numbers = [ [x.lineno, y.lineno ] for chunk_codeline in test_objs for x, y in [chunk_codeline] ]
        expected_new_line_numbers = [ [i, i+1] for i in range(0, 99, 2)]

        self.assertEqual(new_line_numbers, expected_new_line_numbers)
        self.assertNotEqual(line_numbers, new_line_numbers)

        # Rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj-= 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for -=: <class 'float'>")


    def test_iadd(self):

        test_obj = self.gen_codeline_obj(0)
        test_obj += 1
        self.assertEqual(test_obj.lineno,  1)

        test_obj = self.gen_codeline_obj(500_000)
        test_obj += 1
        self.assertEqual(test_obj.lineno,  500_001)

        # Rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj += 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for +=: <class 'float'>")

    def test_gt(self):

        # Both lhs and rhs are Codelines
        test_obj_smaller = self.gen_codeline_obj(10)
        test_obj_greater = self.gen_codeline_obj(20)
        self.assertGreater(test_obj_greater, test_obj_smaller)

        # Just lhs is a Codeline and rhs is int
        self.assertGreater(test_obj_greater, 10)

        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj_greater > 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for >: <class 'float'>")

    def test_lt(self):

        # Both lhs and rhs are Codelines
        test_obj_smaller = self.gen_codeline_obj(10)
        test_obj_greater = self.gen_codeline_obj(20)
        self.assertLess(test_obj_smaller, test_obj_greater)

        # Just lhs is a Codeline and rhs is int
        self.assertLess(test_obj_smaller, 20)

        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj_smaller < None

        self.assertEqual(str(cm.exception), "Unsupported type for <: <class 'NoneType'>")

    def test_ge(self):

        # Similar as above
        test_obj_smaller = self.gen_codeline_obj(10)
        test_obj_greater = self.gen_codeline_obj(20)
        test_obj_equal   = self.gen_codeline_obj(20)
        self.assertGreaterEqual(test_obj_greater, test_obj_smaller)
        self.assertGreaterEqual(test_obj_greater, test_obj_equal)

        # Just lhs is a Codeline and rhs is int
        self.assertGreaterEqual(test_obj_greater, 10)
        self.assertGreaterEqual(test_obj_greater, 20)

        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj_greater >= "Whoopsie!"

        self.assertEqual(str(cm.exception), "Unsupported type for >=: <class 'str'>")

    def test_le(self):

        # Both lhs and rhs are Codelines
        test_obj_smaller = self.gen_codeline_obj(10)
        test_obj_greater = self.gen_codeline_obj(20)
        test_obj_equal   = self.gen_codeline_obj(10)
        self.assertLessEqual(test_obj_smaller, test_obj_greater)
        self.assertLessEqual(test_obj_smaller, test_obj_equal)

        # Just lhs is a Codeline and rhs is int
        self.assertLessEqual(test_obj_smaller, 20)
        self.assertLessEqual(test_obj_smaller, 10)

        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj_smaller <= []

        self.assertEqual(str(cm.exception), "Unsupported type for <=: <class 'list'>")

    def test_ne(self):

        # Both lhs and rhs are Codelines
        test_obj_a = self.gen_codeline_obj(10)
        test_obj_b = self.gen_codeline_obj(20)
        self.assertNotEqual(test_obj_a, test_obj_b)

        # Just lhs is a Codeline and rhs is int
        self.assertNotEqual(test_obj_a, 20)
        self.assertNotEqual(test_obj_b, 10)

        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj_a != 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for !=: <class 'float'>")

    def test_eq(self):

        # Both lhs and rhs are Codelines
        test_obj_a = self.gen_codeline_obj(10)
        test_obj_b = self.gen_codeline_obj(10)
        self.assertEqual(test_obj_a, test_obj_b)

        # Just lhs is a Codeline and rhs is int
        self.assertEqual(test_obj_a, 10)

        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj_a == "Another Whoopsie!"

        self.assertEqual(str(cm.exception), "Unsupported type for ==: <class 'str'>")

class ISATest(unittest.TestCase):

    @staticmethod
    def gen_isa(isa : pathlib.Path = pathlib.Path("mock_isalang")) -> asm.ISA:
        return asm.ISA(isa)

    @staticmethod
    def resolve_fname(filename : str) -> pathlib.Path:
        return pathlib.Path(filename).resolve()

    @staticmethod
    def reset_isa_singleton(isa : asm.ISA) -> None:
        """The isa object is Singleton. To avoid collisions
        with other tests, the Singleton must be destroyed."""
        singleton_metaclass = isa.__class__.__class__
        isa_class = isa.__class__

        del singleton_metaclass._instances[isa_class]

    def test_singleton(self):

        with mock.patch("builtins.open", mock.mock_open()) as mocked_open:

            test_obj_a = self.gen_isa(pathlib.Path("mock_filename_a"))
            test_obj_b = self.gen_isa(pathlib.Path("mock_filename_b"))

            # Check with various ways that the object is the same
            self.assertIs(test_obj_a, test_obj_b)
            self.assertEqual(test_obj_a, test_obj_b)
            self.assertEqual(id(test_obj_a), id(test_obj_b))

            # Check that the source of obj_b is not the invalid_isalang.isa
            # but the source of obj_a
            self.assertNotEqual(test_obj_b.source, f"{os.getcwd()}/dummy_isalang/invalid_isalang.isa")
            self.assertEqual(test_obj_b.source, test_obj_a.source)

            self.reset_isa_singleton(test_obj_a)

    def test_constructor(self):

        with mock.patch("builtins.open", mock.mock_open()) as mocked_open:

            mocked_open.side_effect = FileNotFoundError

            with self.assertRaises(SystemExit) as cm:

                self.gen_isa(pathlib.Path("an_invalid/path.isa"))

            self.assertEqual(cm.exception.code, 1)

        invalid_mock_text = r"""#commentline
        valid_line
        invalid line"""

        with mock.patch("builtins.open", mock.mock_open(read_data=invalid_mock_text)) as mocked_open:

            with self.assertRaises(SyntaxError) as cm:
                test_obj = self.gen_isa(pathlib.Path("mock_filename"))

        self.assertEqual(str(cm.exception),
            f"Wrong syntax at line 3 of {os.getcwd()}/mock_filename file")

        invalid_mock_text = r"""valid_line
        another_valid_line

        whoopsie empty line above"""

        with mock.patch("builtins.open", mock.mock_open(read_data=invalid_mock_text)) as mocked_open:

            with self.assertRaises(SyntaxError) as cm:
                test_obj = self.gen_isa(pathlib.Path("mock_filename"))

        self.assertEqual(str(cm.exception),
            f"Empty line at line number 3 of {os.getcwd()}/mock_filename file")

        mock_instructions = "instruction_a\ninstruction_b\ninstruction_c"
        with mock.patch("builtins.open", mock.mock_open(read_data=mock_instructions)) as mocked_open:
            test_obj = self.gen_isa(pathlib.Path("mock_filename"))
            self.assertCountEqual(test_obj.mnemonics, {"instruction_a", "instruction_b", "instruction_c"})

        self.reset_isa_singleton(test_obj)

    def test_repr(self):

        with mock.patch("builtins.open", mock.mock_open()) as mocked_open:
            test_obj = self.gen_isa(pathlib.Path("mock_filename"))
            self.assertEqual(repr(test_obj), f"ISA({self.resolve_fname('mock_filename')})")

        self.reset_isa_singleton(test_obj)

    def test_get_mnemonics(self):
        mock_instructions = "instruction_a\ninstruction_b\ninstruction_c"
        with mock.patch("builtins.open", mock.mock_open(read_data = mock_instructions)) as mocked_open:
            test_obj = self.gen_isa()
            mnemonics = test_obj.get_mnemonics()

        self.assertCountEqual(mnemonics, {"instruction_a", "instruction_b", "instruction_c"})

        self.reset_isa_singleton(test_obj)

    def test_is_instruction(self):
        mock_instructions = "instruction_a\ninstruction_b\ninstruction_c"
        with mock.patch("builtins.open", mock.mock_open(read_data = mock_instructions)) as mocked_open:
            test_obj = self.gen_isa()

        self.assertFalse(test_obj.is_instruction("definitely_no"))
        self.assertTrue(test_obj.is_instruction("instruction_a"))

        self.reset_isa_singleton(test_obj)

class AssemblyHandlerTest(unittest.TestCase):

    EXPECTED_CANDIDATES = [
        [asm.Codeline(8, "addi sp, sp, -112 # allocate 112 bytes on the stack", valid_insn = True)],
        [asm.Codeline(9, "sw ra, 104(sp) # save return address", valid_insn = True)],
        [asm.Codeline(10, "sw s0, 96(sp) # save callee-saved registers", valid_insn = True)],
        [asm.Codeline(11, "sw s1, 88(sp)", valid_insn = True)],
        [asm.Codeline(12, "sw s2, 80(sp)", valid_insn = True)],
        [asm.Codeline(13, "sw s3, 72(sp)", valid_insn = True)],
        [asm.Codeline(14, "sw s4, 64(sp)", valid_insn = True)],
        [asm.Codeline(15, "sw s5, 56(sp)", valid_insn = True)],
        [asm.Codeline(16, "sw s6, 48(sp)", valid_insn = True)],
        [asm.Codeline(17, "sw s7, 40(sp)", valid_insn = True)],
        [asm.Codeline(18, "sw s8, 32(sp)", valid_insn = True)],
        [asm.Codeline(19, "sw s9, 24(sp)", valid_insn = True)],
        [asm.Codeline(20, "sw s10, 16(sp)", valid_insn = True)],
        [asm.Codeline(21, "sw s11, 8(sp)", valid_insn = True)],
        [asm.Codeline(22, "addi s0, sp, 112 # set up s0 to point to start of stack frame", valid_insn = True)]
    ]

    EXPECTED_CODE =  [
        asm.Codeline(8, "addi sp, sp, -112 # allocate 112 bytes on the stack", valid_insn = True),
        asm.Codeline(9, "sw ra, 104(sp) # save return address", valid_insn = True),
        asm.Codeline(10, "sw s0, 96(sp) # save callee-saved registers", valid_insn = True),
        asm.Codeline(11, "sw s1, 88(sp)", valid_insn = True),
        asm.Codeline(12, "sw s2, 80(sp)", valid_insn = True),
        asm.Codeline(13, "sw s3, 72(sp)", valid_insn = True),
        asm.Codeline(14, "sw s4, 64(sp)", valid_insn = True),
        asm.Codeline(15, "sw s5, 56(sp)", valid_insn = True),
        asm.Codeline(16, "sw s6, 48(sp)", valid_insn = True),
        asm.Codeline(17, "sw s7, 40(sp)", valid_insn = True),
        asm.Codeline(18, "sw s8, 32(sp)", valid_insn = True),
        asm.Codeline(19, "sw s9, 24(sp)", valid_insn = True),
        asm.Codeline(20, "sw s10, 16(sp)", valid_insn = True),
        asm.Codeline(21, "sw s11, 8(sp)", valid_insn = True),
        asm.Codeline(22, "addi s0, sp, 112 # set up s0 to point to start of stack frame", valid_insn = True)
    ]

    @staticmethod
    def gen_rv_handler(assembly_source : pathlib.Path = pathlib.Path("assembly/riscv_test.S"), chunksize : int = 1) -> asm.AssemblyHandler:
        isa = asm.ISA(pathlib.Path("../../langs/riscv.isa"))
        return asm.AssemblyHandler(isa, assembly_source, chunksize)

    @staticmethod
    def reset_isa_singleton(handler : asm.AssemblyHandler) -> None:
        """The self.isa of the handler object is Singleton.
        To avoid collisions with other tests, the Singleton
        must be destroyed."""
        singleton_metaclass = handler.isa.__class__.__class__
        isa_class = handler.isa.__class__

        del singleton_metaclass._instances[isa_class]

    def test_constructor(self):

        isa = asm.ISA(pathlib.Path("../../langs/riscv.isa"))

        # manually generating the handler because ISA also uses  open()
        # and we don't want it to be intercepted as it has been already
        # tested.
        with mock.patch("builtins.open", mock.mock_open()) as mocked_open:

            mocked_open.side_effect = FileNotFoundError

            with self.assertRaises(SystemExit) as cm:

                test_obj = asm.AssemblyHandler(isa = isa,
                    assembly_source = pathlib.Path("an_invalid/assembly_source_path.S"),
                    chunksize = 1)

            self.assertEqual(cm.exception.code, 1)

        test_obj = self.gen_rv_handler()

        self.assertEqual(self.EXPECTED_CANDIDATES, test_obj.candidates)
        self.assertEqual(test_obj.get_code(), self.EXPECTED_CODE)

        self.reset_isa_singleton(test_obj)

    def test_get_asm_source(self):

        test_obj = self.gen_rv_handler()
        self.assertEqual(str(test_obj.get_asm_source()), f"{os.getcwd()}/assembly/riscv_test.S")
        self.reset_isa_singleton(test_obj)

    def test_get_code(self):

        test_obj = self.gen_rv_handler()

        self.assertEqual(test_obj.get_code(), self.EXPECTED_CODE)

        self.reset_isa_singleton(test_obj)

    def test_get_random_candidate(self):

        test_obj = self.gen_rv_handler()

        # Get and do NOT pop the candidate
        random_candidate = test_obj.get_random_candidate(pop_candidate=False)
        new_candidates = [x for sublist in test_obj.candidates for x in sublist]
        self.assertIn(random_candidate, new_candidates)

        # Get and pop the candidate
        random_candidate = test_obj.get_random_candidate(pop_candidate = True)
        new_candidates = [x for sublist in test_obj.candidates for x in sublist]
        self.assertNotIn(random_candidate, new_candidates)

        self.reset_isa_singleton(test_obj)

    def test_get_candidate(self):

        test_obj = self.gen_rv_handler()

        # Everything works as expected. Candidate exists
        expected_candidate = asm.Codeline(10, "sw s1, 88(sp)", True)
        self.assertEqual(test_obj.get_candidate(10), expected_candidate)
        self.reset_isa_singleton(test_obj)

        # Candidate does not exist
        with self.assertRaises(LookupError) as cm:

            test_obj.get_candidate(666)

        self.assertEqual(str(cm.exception), f"Requested Codeline with lineno=666 not found!")

    def test_set_test_application_time(self):

        test_obj = self.gen_rv_handler()
        self.assertIsNone(test_obj.test_application_time)

        time_value = int(random.random())
        test_obj.set_test_application_time(time_value)
        self.assertEqual(time_value, test_obj.test_application_time)
        self.reset_isa_singleton(test_obj)

    def test_remove_line_reduction(self):

        """After removing a candidate, the candidates that have a lineno
        > than the just removed one must be updated by reducing their
        lineno attribute by 1 (-=1)."""

        backup = pathlib.Path("assembly/riscv_test.S.bak")
        original = pathlib.Path("assembly/riscv_test.S")
        shutil.copy2(original, backup)

        remove_lineno = 12
        test_obj = self.gen_rv_handler()
        candidate = test_obj.get_candidate(remove_lineno)

        # Deep copy required in order to generate separate
        # asm.Codeline objects here.
        candidates_before = [x for chunk in copy.deepcopy(test_obj.candidates) for x in chunk]
        test_obj.remove(candidate)
        candidates_after = [x for chunk in test_obj.candidates for x in chunk]

        removed_candidate_index = candidates_before.index(candidate)

        for index, (cand_before, cand_after) in enumerate(zip(candidates_before, candidates_after)):

            if index <= removed_candidate_index: continue

            self.assertEqual(cand_before.lineno -1, cand_after.lineno)

        # Also guarantee that the candidate was not popped from the list
        self.assertEqual(removed_candidate_index, candidates_after.index(candidate))

        self.reset_isa_singleton(test_obj)
        shutil.copy2(backup, original)

    def test_remove(self):

        total_lines = 23

        for lineno in range(total_lines):

            test_obj = self.gen_rv_handler()
            try:
                candidate = test_obj.get_candidate(lineno)
            except LookupError:
                continue

            # Create a copy to test remove with the replacement of
            # the original file. Copy it here because the asm_file
            # attribute will be modified by the first remove  call
            temp_file = pathlib.Path(f"{test_obj.asm_file}.orig")
            shutil.copy2(test_obj.asm_file, temp_file)

            test_obj.remove(candidate)

            # Check that the assembly source remains the same.
            expected_file = pathlib.Path(f"assembly/riscv_test.S")
            self.assertTrue(expected_file.exists())
            self.assertEqual(str(test_obj.asm_file), str(expected_file.resolve()))

            new_test_obj = self.gen_rv_handler(expected_file)

            # Check that new assembly file does not contain the candidate
            # i.e., diff the two files
            self.assertNotIn(str(candidate), [str(x) for x in new_test_obj.get_code()])

            # Ensure that the candidate is present in the old one.
            self.assertIn(str(candidate), [str(x) for x in test_obj.get_code()])

            shutil.copy2(temp_file, expected_file)
            temp_file.unlink()

            self.reset_isa_singleton(test_obj)

    def test_restore(self):

        total_lines = 23

        backup = pathlib.Path("assembly/riscv_test.S.bak")
        original = pathlib.Path("assembly/riscv_test.S")

        shutil.copy2(original, backup)

        for lineno in range(total_lines):

            test_obj = self.gen_rv_handler()

            try:
                candidate = test_obj.get_candidate(lineno)
            except LookupError:
                continue

            test_obj.remove(candidate)

            # Check changelog entries
            self.assertEqual(test_obj.asm_file_changelog, [candidate])

            test_obj.restore()

            # Check again that changelog is empty now
            self.assertEqual(test_obj.asm_file_changelog, [])

            # Test the differences of the files
            test_obj_new = self.gen_rv_handler(test_obj.asm_file)

            # The code must be the same after restoration
            self.assertEqual(len(test_obj.get_code()), len(test_obj_new.get_code()))
            self.assertEqual(test_obj.get_code(), test_obj_new.get_code())

            self.reset_isa_singleton(test_obj)

        shutil.copy2(backup, original)
        backup.unlink()

    def test_save(self):

        total_lines = 23

        backup = pathlib.Path("assembly/riscv_test.S.bak")
        original = pathlib.Path("assembly/riscv_test.S")

        shutil.copy2(original, backup)

        test_obj = self.gen_rv_handler()
        test_obj.save()

        for lineno in range(total_lines):

            test_obj = self.gen_rv_handler()

            try:
                candidate = test_obj.get_candidate(lineno)
            except LookupError:
                continue

            test_obj.remove(candidate)

            # Check changelog entries
            self.assertEqual(test_obj.asm_file_changelog, [candidate])

            expected_filename = pathlib.Path(f"assembly/riscv_test-{candidate.lineno}.S").resolve()

            test_obj.save()

            # Check that the file has been generated.
            self.assertTrue(expected_filename.exists())

            #expected_filename.unlink()
            self.reset_isa_singleton(test_obj)
            expected_filename.unlink()
            shutil.copy2(backup, original)

        shutil.copy2(backup,original)
        backup.unlink()


