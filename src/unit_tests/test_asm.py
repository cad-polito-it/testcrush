#!/usr/bin/python3

try:

    from testcrush import asm

except ModuleNotFoundError:

    import sys
    sys.path.append("..")
    from testcrush import asm

import unittest
import unittest.mock as mock

import pathlib
import os
import copy
import shutil
import random


class CodelineTest(unittest.TestCase):

    @staticmethod
    def gen_codeline_obj(lineno: int, data: str = "Dummy Text", valid_insn: bool = True):
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

    def test_isub_with_random_sequence(self):

        random_100_non_zero_int = [random.randint(1, sys.maxsize) for _ in range(100)]

        # Test similar to struct appearing in the asm.py code for modifying codelines in candidates
        test_objs = [[self.gen_codeline_obj(random_100_non_zero_int[i]),
                      self.gen_codeline_obj(random_100_non_zero_int[i+1])]
                     for i in range(0, len(random_100_non_zero_int), 2)]

        line_numbers = [[x.lineno, y.lineno] for chunk_codeline in test_objs for x, y in [chunk_codeline]]

        for chunk in test_objs:
            for chunk_codeline in chunk:
                chunk_codeline -= 1

        new_line_numbers = [[x.lineno, y.lineno] for chunk_codeline in test_objs for x, y in [chunk_codeline]]
        expected_new_line_numbers = [[random_100_non_zero_int[i]-1,
                                      random_100_non_zero_int[i+1]-1]
                                     for i in range(0, len(random_100_non_zero_int), 2)]

        self.assertEqual(new_line_numbers, expected_new_line_numbers)
        self.assertNotEqual(line_numbers, new_line_numbers)

    def test_isub_type_error(self):

        random_non_zero_int = random.randint(1, sys.maxsize)
        test_obj = self.gen_codeline_obj(random_non_zero_int)
        # Rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj -= 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for -=: <class 'float'>")


    def test_iadd_with_random_codeline(self):

        random_int = random.randint(0, sys.maxsize)
        test_obj = self.gen_codeline_obj(random_int)
        test_obj += 1
        self.assertEqual(test_obj.lineno,  random_int+1)

    def test_isub_with_random_sequence(self):

        random_100_non_zero_int = [random.randint(0, sys.maxsize) for _ in range(100)]

        test_objs = [
            [self.gen_codeline_obj(random_100_non_zero_int[i]),
            self.gen_codeline_obj(random_100_non_zero_int[i+1])] for i in range(0,len(random_100_non_zero_int),2)]

        line_numbers = [[x.lineno, y.lineno ] for chunk_codeline in test_objs for x, y in [chunk_codeline]]

        for chunk in test_objs:
            for chunk_codeline in chunk:
                chunk_codeline += 1

        new_line_numbers = [[x.lineno, y.lineno ] for chunk_codeline in test_objs for x, y in [chunk_codeline]]
        expected_new_line_numbers = [
            [random_100_non_zero_int[i]+1,
            random_100_non_zero_int[i+1]+1] for i in range(0,len(random_100_non_zero_int),2)]

        self.assertEqual(new_line_numbers, expected_new_line_numbers)
        self.assertNotEqual(line_numbers, new_line_numbers)

    def test_iadd_type_error(self):

        random_int = random.randint(0, sys.maxsize)
        test_obj = self.gen_codeline_obj(random_int)

        with self.assertRaises(TypeError) as cm:
            test_obj += 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for +=: <class 'float'>")

    def test_gt_with_codeline(self):

        random_int = random.randint(0, sys.maxsize)
        greater_random_int = random_int + random.randint(1, sys.maxsize - random_int)

        test_obj_smaller = self.gen_codeline_obj(random_int)
        test_obj_greater = self.gen_codeline_obj(greater_random_int)

        self.assertGreater(test_obj_greater, test_obj_smaller)

    def test_gt_with_int(self):

        random_int = random.randint(1, sys.maxsize)
        random_smaller_int = random.randint(0, random_int - 1)

        test_obj = self.gen_codeline_obj(random_int)

        # Just lhs is a Codeline and rhs is int
        self.assertGreater(test_obj,
                           test_obj.lineno - random_smaller_int)

    def test_gt_type_error(self):

        test_obj = self.gen_codeline_obj(random.randint(0, sys.maxsize))

        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj > 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for >: <class 'float'>")

    def test_lt(self):

        random_int = random.randint(0, sys.maxsize)
        greater_random_int = random_int + random.randint(1, sys.maxsize - random_int)

        test_obj_smaller = self.gen_codeline_obj(random_int)
        test_obj_greater = self.gen_codeline_obj(greater_random_int)

        self.assertLess(test_obj_smaller, test_obj_greater)

    def test_lt_with_int(self):

        random_int = random.randint(0, sys.maxsize)
        greater_random_int = random_int + random.randint(1, sys.maxsize - random_int)

        test_obj_smaller = self.gen_codeline_obj(random_int)

        self.assertLess(test_obj_smaller, greater_random_int)

    def test_lt_type_error(self):

        test_obj = self.gen_codeline_obj(random.randint(0, sys.maxsize))
        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj < 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for <: <class 'float'>")

    def test_ge_with_codeline(self):

        random_int = random.randint(0, sys.maxsize)
        greater_random_int = random_int + random.randint(1, sys.maxsize - random_int)

        test_obj = self.gen_codeline_obj(random_int)
        test_obj_greater = self.gen_codeline_obj(greater_random_int)
        test_obj_equal   = self.gen_codeline_obj(random_int)

        self.assertGreaterEqual(test_obj_greater, test_obj)
        self.assertGreaterEqual(test_obj_greater, test_obj_equal)

    def test_ge_with_int(self):

        random_int = random.randint(0, sys.maxsize)
        greater_random_int = random_int + random.randint(1, sys.maxsize - random_int)

        test_obj = self.gen_codeline_obj(greater_random_int)

        self.assertGreaterEqual(test_obj, random_int)
        self.assertGreaterEqual(test_obj, random_int)

    def test_ge_type_error(self):

        test_obj = self.gen_codeline_obj(random.randint(0, sys.maxsize))

        # Lhs is Codeline but rhs is an unsupported type
        with self.assertRaises(TypeError) as cm:
            test_obj >= "Whoopsie!"

        self.assertEqual(str(cm.exception), "Unsupported type for >=: <class 'str'>")

    def test_le_with_codeline(self):

        random_int = random.randint(0, sys.maxsize)
        greater_random_int = random_int + random.randint(1, sys.maxsize - random_int)

        test_obj = self.gen_codeline_obj(random_int)
        test_obj_greater = self.gen_codeline_obj(greater_random_int)
        test_obj_equal   = self.gen_codeline_obj(random_int)

        # Both lhs and rhs are Codelines
        test_obj = self.gen_codeline_obj(test_obj)
        test_obj_greater = self.gen_codeline_obj(test_obj_greater)
        test_obj_equal   = self.gen_codeline_obj(test_obj)

        self.assertLessEqual(test_obj, test_obj_greater)
        self.assertLessEqual(test_obj, test_obj_equal)

    def test_le_with_int(self):

        random_int = random.randint(0, sys.maxsize)
        greater_random_int = random_int + random.randint(1, sys.maxsize - random_int)

        test_obj = self.gen_codeline_obj(random_int)

        self.assertLessEqual(test_obj, greater_random_int)
        self.assertLessEqual(test_obj, random_int)

    def test_le_type_error(self):

        test_obj = self.gen_codeline_obj(random.randint(0, sys.maxsize))

        with self.assertRaises(TypeError) as cm:
            test_obj <= []

        self.assertEqual(str(cm.exception), "Unsupported type for <=: <class 'list'>")

    def test_ne_with_codeline(self):

        random_int_1 = random.randint(0, sys.maxsize)
        random_int_2 = random.randint(0, sys.maxsize)
        while random_int_2 == random_int_1:
            random_int_2 = random.randint(0, sys.maxsize)

        # Both lhs and rhs are Codelines
        test_obj_a = self.gen_codeline_obj(random_int_1)
        test_obj_b = self.gen_codeline_obj(random_int_2)
        self.assertNotEqual(test_obj_a, test_obj_b)

    def test_ne_with_int(self):

        random_int_1 = random.randint(0, sys.maxsize)
        random_int_2 = random.randint(0, sys.maxsize)
        while random_int_2 == random_int_1:
            random_int_2 = random.randint(0, sys.maxsize)

        test_obj_a = self.gen_codeline_obj(random_int_1)
        test_obj_b = self.gen_codeline_obj(random_int_2)

        self.assertNotEqual(test_obj_a, random_int_2)
        self.assertNotEqual(test_obj_b, random_int_1)

    def test_ne_type_error(self):

        test_obj = self.gen_codeline_obj(random.randint(0, sys.maxsize))

        with self.assertRaises(TypeError) as cm:
            test_obj != 3.14

        self.assertEqual(str(cm.exception), "Unsupported type for !=: <class 'float'>")

    def test_eq_with_codeline(self):

        random_int = random.randint(0, sys.maxsize)

        test_obj_a = self.gen_codeline_obj(random_int)
        test_obj_b = self.gen_codeline_obj(random_int)
        self.assertEqual(test_obj_a, test_obj_b)

    def test_eq_with_int(self):

        random_int = random.randint(0, sys.maxsize)

        test_obj = self.gen_codeline_obj(random_int)

        self.assertEqual(test_obj, random_int)

    def test_eq_type_error(self):

        random_int = random.randint(0, sys.maxsize)

        test_obj = self.gen_codeline_obj(random_int)

        with self.assertRaises(TypeError) as cm:
            test_obj == "Another Whoopsie!"

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
        """
        The isa object is Singleton. To avoid collisions
        with other tests, the Singleton must be destroyed.
        """
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

    def test_constructor_file_not_found(self):

        with mock.patch("builtins.open", mock.mock_open()) as mocked_open:

            mocked_open.side_effect = FileNotFoundError

            with self.assertRaises(SystemExit) as cm:

                self.gen_isa(pathlib.Path("an_invalid/path.isa"))

            self.assertEqual(cm.exception.code, 1)

    def test_constructor_syntax_error(self):

        invalid_mock_text = r"""#commentline
        valid_line
        invalid line"""

        with mock.patch("builtins.open", mock.mock_open(read_data=invalid_mock_text)) as mocked_open:

            with self.assertRaises(SyntaxError) as cm:
                test_obj = self.gen_isa(pathlib.Path("mock_filename"))

        self.assertEqual(str(cm.exception),
            f"Wrong syntax at line 3 of {os.getcwd()}/mock_filename file")

    def test_constructor_empty_line_error(self):

        invalid_mock_text = r"""valid_line
        another_valid_line

        whoopsie empty line above"""

        with mock.patch("builtins.open", mock.mock_open(read_data=invalid_mock_text)) as mocked_open:

            with self.assertRaises(SyntaxError) as cm:
                test_obj = self.gen_isa(pathlib.Path("mock_filename"))

        self.assertEqual(str(cm.exception),
            f"Empty line at line number 3 of {os.getcwd()}/mock_filename file")

    def test_constructor_success(self):

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

    RISCV_ISALANG = r"""\
# pseudo ops #
li
la
mv
not
neg
bgt
ble
bgtu
bleu
beqz
bnez
bgez
blez
bgtz
j
call
ret
nop
# rv32i #
lui
auipc
jal
jalr
beq
bne
blt
bge
bltu
bgeu
lb
lh
lw
lbu
lhu
sb
sh
sw
addi
slti
sltiu
xori
ori
andi
slli
srli
srai
add
sub
sll
slt
sltu
xor
srl
sra
or
and
fence
ecall
ebreak
# rv32m #
mul
mulh
mulhsu
mulhu
div
divu
rem
remu
# rv32c #
c.addi4spn
c.lw
c.sw
c.addi
c.nop
c.jal
c.li
c.lui
c.addi16sp
c.srli
c.srai
c.andi
c.sub
c.xor
c.or
c.and
c.j
c.beqz
c.bnez
c.slli
c.lwsp
c.mv
c.jr
c.add
c.jalr
c.ebreak
c.swsp
# rvzicsr #
csrrw
csrrs
csrrc
csrrwi
csrrsi
csrrci
# rvzifencei #
fence.i
# rv32f #
flw
fsw
fmadd.s
fmsub.s
fnmadd.s
fnmsub.s
fadd.s
fsub.s
fmul.s
fdiv.s
fsqrt.s
fsgnj.s
fsgnjn.s
fsgnjx.s
fmin.s
fmax.s
fcvt.w.s
fcvt.wu.s
feq.s
flt.s
fle.s
fclass.s
fcvt.s.w
fcvt.s.wu
fmv.x.w
fmv.w.x
# rv32fc #
c.flw
c.fsw
c.flwsp
c.fswsp
# rv32a #
lrw
scw
amoswapw
amoaddw
amoxorw
amoandw
amoorw
amominw
amomaxw
amominuw
amomaxuw
# rv32d #
fld
fsd
fmadd.d
fmsub.d
fnmadd.d
fnmsub.d
fadd.d
fsub.d
fmul.d
fdiv.d
fsqrt.d
fsgnj.d
fsgnjn.d
fsgnjx.d
fmin.d
fmax.d
fcvt.s.d
fcvt.d.s
feq.d
flt.d
fle.d
fclass.d
fcvt.w.d
fcvt.wu.d
fcvt.d.w
fcvt.d.wu
# rv32dc #
c.fld
c.fsd
c.fldsp
c.fsdsp"""

    RISCV_SNIPPET = r"""section .text
.global test1
.type test1, @function
test_result:
		.space 1024

test1:
	# ABI prologue
	addi sp, sp, -112     # allocate 112 bytes on the stack
	sw ra, 104(sp)        # save return address
	sw s0, 96(sp)         # save callee-saved registers
	sw s1, 88(sp)
	sw s2, 80(sp)
	sw s3, 72(sp)
	sw s4, 64(sp)
	sw s5, 56(sp)
	sw s6, 48(sp)
	sw s7, 40(sp)
	sw s8, 32(sp)
	sw s9, 24(sp)
	sw s10, 16(sp)
	sw s11, 8(sp)
	addi s0, sp, 112     # set up s0 to point to start of stack frame
"""

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

    def gen_rv_handler(self, assembly_source: pathlib.Path = pathlib.Path("mock_riscv_file"), chunksize: int = 1):

        with mock.patch("builtins.open", mock.mock_open(read_data=self.RISCV_ISALANG)) as mocked_open:
            isa = asm.ISA(pathlib.Path("some_path"))

        if assembly_source.name == "mock_riscv_file":
            with mock.patch("builtins.open", mock.mock_open(read_data=self.RISCV_SNIPPET)) as mocked_open:
                return asm.AssemblyHandler(isa, assembly_source, chunksize)
        else:
            return asm.AssemblyHandler(isa, assembly_source, chunksize)

    @staticmethod
    def reset_isa_singleton(handler : asm.AssemblyHandler) -> None:
        """
        The self.isa of the handler object is Singleton.
        To avoid collisions with other tests, the Singleton
        must be destroyed.
        """
        singleton_metaclass = handler.isa.__class__.__class__
        isa_class = handler.isa.__class__

        del singleton_metaclass._instances[isa_class]

    def test_constructor(self):

        with mock.patch("builtins.open", mock.mock_open(read_data=self.RISCV_ISALANG)) as mocked_open:
            isa = asm.ISA(pathlib.Path("some_path"))

        # manually generating the handler because ISA also uses  open()
        # and we don't want it to be intercepted as it has been already
        # tested.
        with mock.patch("builtins.open", mock.mock_open()) as mocked_open:

            mocked_open.side_effect = FileNotFoundError

            with self.assertRaises(SystemExit) as cm:

                test_obj = asm.AssemblyHandler(isa = asm.ISA(pathlib.Path("../../langs/riscv.irsa")),
                    assembly_source = pathlib.Path("an_invalid/assembly_source_path.S"),
                    chunksize = 1)

            self.assertEqual(cm.exception.code, 1)

        test_obj = self.gen_rv_handler()
        #print(test_obj.candidates)
        self.assertEqual(test_obj.candidates, self.EXPECTED_CANDIDATES)
        self.assertEqual(test_obj.get_code(), self.EXPECTED_CODE)

        self.reset_isa_singleton(test_obj)

    def test_get_asm_source(self):

        test_obj = self.gen_rv_handler()

        self.assertEqual(str(test_obj.get_asm_source()), f"{os.getcwd()}/mock_riscv_file")

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
        expected_candidate = random.choice(self.EXPECTED_CODE)
        self.assertEqual(test_obj.get_candidate(expected_candidate.lineno), expected_candidate)
        self.reset_isa_singleton(test_obj)

        # Candidate does not exist
        with self.assertRaises(LookupError) as cm:

            test_obj.get_candidate(sys.maxsize - 1)

        self.assertEqual(str(cm.exception), f"Requested Codeline with lineno={sys.maxsize - 1} not found!")

    def test_remove_line_reduction(self):
        """
        After removing a candidate, the candidates that have a lineno
        > than the just removed one must be updated by reducing their
        lineno attribute by 1 (-=1).
        """

        remove_lineno = random.choice([x.lineno for x in self.EXPECTED_CODE])
        test_obj = self.gen_rv_handler()
        candidate = test_obj.get_candidate(remove_lineno)

        # Deep copy required in order to generate separate
        # asm.Codeline objects here.
        candidates_before = [x for chunk in copy.deepcopy(test_obj.candidates) for x in chunk]

        with mock.patch("builtins.open", mock.mock_open(read_data=self.RISCV_SNIPPET)):

            test_obj.remove(candidate)

        candidates_after = [x for chunk in test_obj.candidates for x in chunk]

        removed_candidate_index = candidates_before.index(candidate)

        for index, (cand_before, cand_after) in enumerate(zip(candidates_before, candidates_after)):

            if index <= removed_candidate_index: continue

            self.assertEqual(cand_before.lineno -1, cand_after.lineno)

        # Also guarantee that the candidate was not popped from the list
        self.assertEqual(removed_candidate_index, candidates_after.index(candidate))

        pathlib.Path("mock_riscv_file").unlink()
        self.reset_isa_singleton(test_obj)

    def test_remove(self):

        total_lines = len(self.EXPECTED_CODE)

        for lineno in range(total_lines):

            # Generate a temporary .S file
            with open("temp_asm.S", 'w') as outf:
                outf.write(self.RISCV_SNIPPET)

            test_obj = self.gen_rv_handler(assembly_source=pathlib.Path("temp_asm.S"))

            try:
                candidate = test_obj.get_candidate(lineno)
            except LookupError:  # lineno does not correspond to a candidate
                continue

            # Create a copy to test remove with the replacement of
            # the original file. Copy it here because the asm_file
            # attribute will be modified by the first remove  call
            temp_file = pathlib.Path(f"{test_obj.asm_file}.orig")
            shutil.copy2(test_obj.asm_file, temp_file)

            test_obj.remove(candidate)

            # Check that the assembly source remains the same.
            expected_file = pathlib.Path("temp_asm.S")
            self.assertTrue(expected_file.exists())
            self.assertEqual(str(test_obj.asm_file), str(expected_file.resolve()))

            new_test_obj = self.gen_rv_handler(expected_file)
            # Check that new assembly file does not contain the candidate
            # i.e., diff the two files...
            self.assertNotIn(str(candidate), [str(x) for x in new_test_obj.get_code()])

            # But ensure that the candidate is present in the old one.
            self.assertIn(str(candidate), [str(x) for x in test_obj.get_code()])

            # Cleanup
            shutil.copy2(temp_file, expected_file)
            temp_file.unlink()

            self.reset_isa_singleton(test_obj)

        pathlib.Path("temp_asm.S").unlink()

    def test_restore(self):

        total_lines = len(self.EXPECTED_CODE)

        for lineno in range(total_lines):

           # Generate a temporary .S file
            with open("temp_asm.S", 'w') as outf:
                outf.write(self.RISCV_SNIPPET)

            test_obj = self.gen_rv_handler(pathlib.Path("temp_asm.S"))

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

        pathlib.Path("temp_asm.S").unlink()

    def test_save(self):

        total_lines = len(self.EXPECTED_CODE)

        for lineno in range(total_lines):

           # Generate a temporary .S file
            with open("temp_asm.S", 'w') as outf:
                outf.write(self.RISCV_SNIPPET)

            test_obj = self.gen_rv_handler(pathlib.Path("temp_asm.S"))

            try:
                candidate = test_obj.get_candidate(lineno)
            except LookupError:
                continue

            test_obj.remove(candidate)

            # Check changelog entries
            self.assertEqual(test_obj.asm_file_changelog, [candidate])

            expected_filename = pathlib.Path(f"temp_asm-{candidate.lineno}.S").resolve()

            test_obj.save()

            # Check that the file has been generated.
            self.assertTrue(expected_filename.exists())

            #expected_filename.unlink()
            self.reset_isa_singleton(test_obj)
            expected_filename.unlink()

        pathlib.Path("temp_asm.S").unlink()
