#!/usr/bin/python3
import sys
sys.path.append("../")

import unittest
import unittest.mock as mock
import asm
import pathlib 
import os

class CodelineTest(unittest.TestCase):
    
    @staticmethod
    def gen_codeline_obj(lineno : int, data : str = "Dummy Text", valid_insn : bool = True):
        return asm.Codeline(lineno, data, valid_insn)

    def test_repr(self):
        
        test_obj = self.gen_codeline_obj(1)
        self.assertEqual(repr(test_obj), f"Codeline(1, \"Dummy Text\", valid_insn = True)")

    def test_str(self):

        test_obj = self.gen_codeline_obj(1)
        self.assertEqual(str(test_obj), "[#1]: Dummy Text")

    def test_isub(self):
        
        # -= 1 for a Codeline with lineno 0 should return 0 as a negative 
        # line of code makes no sense.
        test_obj = self.gen_codeline_obj(0)
        test_obj -= 1
        test_obj_lineno = test_obj.lineno
        self.assertEqual(test_obj_lineno,  0)

        # Normal behavior for non 0 lineno values
        test_obj = self.gen_codeline_obj(100)
        test_obj -= 1
        test_obj_lineno = test_obj.lineno
        self.assertEqual(test_obj_lineno, 99)

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
        test_obj_lineno = test_obj.lineno
        self.assertEqual(test_obj_lineno,  1)

        test_obj = self.gen_codeline_obj(500_000)
        test_obj += 1
        test_obj_lineno = test_obj.lineno
        self.assertEqual(test_obj_lineno,  500_001)

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
            f"Empty line found at line number 3 of {os.getcwd()}/mock_filename file")

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
        asm.Codeline(0, "section .text", valid_insn = False), 
        asm.Codeline(1, ".global test1", valid_insn = False), 
        asm.Codeline(2, ".type test1, @function", valid_insn = False), 
        asm.Codeline(3, "test_result:", valid_insn = False), 
        asm.Codeline(4, ".space 1024", valid_insn = False), 
        asm.Codeline(6, "test1:", valid_insn = False), 
        asm.Codeline(7, "# ABI prologue", valid_insn = False), 
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
    

        self.assertEqual(test_obj.code, self.EXPECTED_CODE)

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
