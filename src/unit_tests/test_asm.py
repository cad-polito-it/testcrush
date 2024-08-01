#!/usr/bin/python3
import sys
sys.path.append("../")

import unittest
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

    
    def test_iadd(self):
        
        test_obj = self.gen_codeline_obj(0)
        test_obj += 1
        test_obj_lineno = test_obj.lineno
        self.assertEqual(test_obj_lineno,  1)

        test_obj = self.gen_codeline_obj(500_000)
        test_obj += 1
        test_obj_lineno = test_obj.lineno
        self.assertEqual(test_obj_lineno,  500_001)

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

        self.assertEqual(cm.exception.__str__(), "Unsupported type for >: <class 'float'>")    

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

        self.assertEqual(cm.exception.__str__(), "Unsupported type for <: <class 'NoneType'>")

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
        
        self.assertEqual(cm.exception.__str__(), "Unsupported type for >=: <class 'str'>")
        
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

        self.assertEqual(cm.exception.__str__(), "Unsupported type for <=: <class 'list'>")

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

        self.assertEqual(cm.exception.__str__(), "Unsupported type for !=: <class 'float'>") 

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

        self.assertEqual(cm.exception.__str__(), "Unsupported type for ==: <class 'str'>") 

class ISATest(unittest.TestCase):

    @staticmethod
    def gen_isa(isa : pathlib.Path = pathlib.Path("dummy_isalang/valid_isalang.isa")) -> asm.ISA:
        return asm.ISA(isa)
    
    @staticmethod
    def resolve_fname(filename : str) -> pathlib.Path:
        return pathlib.Path(filename).resolve()
        
    def test_singleton(self):

        test_obj_a = self.gen_isa()   
        test_obj_b = self.gen_isa(pathlib.Path("dummy_isalang/invalid_isalang.isa"))

        # Check with various ways that the object is the same 
        self.assertIs(test_obj_a, test_obj_b)
        self.assertEqual(test_obj_a, test_obj_b)
        self.assertEqual(id(test_obj_a), id(test_obj_b))
        
        # Check that the source of obj_b is not the invalid_isalang.isa 
        # but the source of obj_a
        self.assertNotEqual(test_obj_b.source, f"{os.getcwd()}/dummy_isalang/invalid_isalang.isa")
        self.assertEqual(test_obj_b.source, test_obj_a.source)

        del test_obj_a, test_obj_b

    def test_constructor(self):
        
        with self.assertRaises(SyntaxError) as cm:
            test_obj = self.gen_isa(pathlib.Path("dummy_isalang/invalid_isalang.isa"))

        self.assertEqual(cm.exception.__str__(),
            f"Wrong syntax at line 3 of {os.getcwd()}/dummy_isalang/invalid_isalang.isa file")
        
        test_obj = self.gen_isa()
        expected_mnemonics = {'instruction_a', 'instruction_c', 'instruction_b'}

        self.assertCountEqual(test_obj.mnemonics, expected_mnemonics)

        del test_obj 

    def test_repr(self):

        test_obj = self.gen_isa()
        self.assertEqual(repr(test_obj), f"ISA({self.resolve_fname('dummy_isalang/valid_isalang.isa')})")
        del test_obj 

    def test_get_mnemonics(self):

        test_obj = self.gen_isa()
        mnemonics = test_obj.get_mnemonics()
        expected_mnemonics = {'instruction_a', 'instruction_c', 'instruction_b'}

        self.assertCountEqual(mnemonics, expected_mnemonics)
        del test_obj

    def test_is_instruction(self):

        test_obj = self.gen_isa()
        self.assertFalse(test_obj.is_instruction("definitely_no"))
        self.assertTrue(test_obj.is_instruction("instruction_a"))