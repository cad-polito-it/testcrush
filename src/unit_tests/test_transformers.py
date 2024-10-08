#!/usr/bin/python3
# SPDX-License-Identifier: MIT

try:

    from testcrush import transformers
    from testcrush import zoix

except ModuleNotFoundError:

    import sys
    sys.path.append("..")
    from testcrush import transformers
    from testcrush import zoix

import unittest
import lark


class FaultListTransformerTest(unittest.TestCase):

    grammar = open("../testcrush/grammars/fault_list.lark").read()
    maxDiff = None
    def get_parser(self):

        return lark.Lark(grammar=self.grammar, start="start", parser="lalr", transformer=transformers.FaultListTransformer())

    def test_stuck_at_fault_list(self):

        parser = self.get_parser()


        fault_list_sample = r"""
            FaultList SAF {
                <  1> ON 0 {PORT "tb.dut.subunit_a.subunit_b.cellA.ZN"}(* "test1"->PC=30551073; "test1"->time="45ns"; *)
                    -- 1 {PORT "tb.dut.subunit_a.subunit_b.cellA.A1"}
                    -- 1 {PORT "tb.dut.subunit_a.subunit_b.cellA.A2"}
                    -- 0 {PORT "tb.dut.subunit_a.subunit_b.operand_b[27:3]"}
            }
        """
        expected_faults = [
            zoix.Fault(Fault_Status='ON', Fault_Type='0', Fault_Sites=['tb.dut.subunit_a.subunit_b.cellA.ZN'], Fault_Attributes={'PC': '30551073', 'time': '45ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='1', Fault_Sites=['tb.dut.subunit_a.subunit_b.cellA.A1']),
            zoix.Fault(Fault_Status='ON', Fault_Type='1', Fault_Sites=['tb.dut.subunit_a.subunit_b.cellA.A2']),
            zoix.Fault(Fault_Status='ON', Fault_Type='0', Fault_Sites=['tb.dut.subunit_a.subunit_b.operand_b[27:3]'])
        ]

        fault_list = parser.parse(fault_list_sample)

        # Manually resolve the fault equivalences
        expected_faults[0].equivalent_faults = 4
        expected_faults[1].equivalent_to = expected_faults[0]
        expected_faults[2].equivalent_to = expected_faults[0]
        expected_faults[3].equivalent_to = expected_faults[0]

        self.assertEqual(fault_list, expected_faults)

    def test_transition_delay_fault_list(self):

        parser = self.get_parser()

        fault_list_sample = r"""
            FaultList TDF {
                <  1> NN F {PORT "tb.dut.subunit_c.U1528.CI"}
                <  1> ON R {PORT "tb.dut.subunit_c.U1528.CO"}(* "test1"->PC_IF=00000d1c; "test1"->sim_time="   8905ns"; *)
                      -- R {PORT "tb.dut.subunit_c.U28.A"}
                <  1> ON F {PORT "tb.dut.subunit_c.U1528.CO"}(* "test1"->PC_IF=00000d1c; "test1"->sim_time="   8905ns"; *)
                      -- F {PORT "tb.dut.subunit_c.U28.A"}
                <  1> ON R {PORT "tb.dut.subunit_c.U1528.S"}(*  "test1"->PC_IF=00000d1c; "test1"->sim_time="   8905ns"; *)
                      -- R {PORT "tb.dut.subunit_c.U27.A"}
                <  1> ON F {PORT "tb.dut.subunit_c.U1528.S"}(*  "test1"->PC_IF=00000d1c; "test1"->sim_time="   8905ns"; *)
                      -- F {PORT "tb.dut.subunit_c.U27.A"}
            }
        """
        expected_faults = [
            zoix.Fault(Fault_Status='NN', Fault_Type='F', Fault_Sites=['tb.dut.subunit_c.U1528.CI']),
            zoix.Fault(Fault_Status='ON', Fault_Type='R', Fault_Sites=['tb.dut.subunit_c.U1528.CO'], Fault_Attributes={'PC_IF': '00000d1c', 'sim_time': '8905ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='R', Fault_Sites=['tb.dut.subunit_c.U28.A']),
            zoix.Fault(Fault_Status='ON', Fault_Type='F', Fault_Sites=['tb.dut.subunit_c.U1528.CO'], Fault_Attributes={'PC_IF': '00000d1c', 'sim_time': '8905ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='F', Fault_Sites=['tb.dut.subunit_c.U28.A']),
            zoix.Fault(Fault_Status='ON', Fault_Type='R', Fault_Sites=['tb.dut.subunit_c.U1528.S'], Fault_Attributes={'PC_IF': '00000d1c', 'sim_time': '8905ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='R', Fault_Sites=['tb.dut.subunit_c.U27.A']),
            zoix.Fault(Fault_Status='ON', Fault_Type='F', Fault_Sites=['tb.dut.subunit_c.U1528.S'], Fault_Attributes={'PC_IF': '00000d1c', 'sim_time': '8905ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='F', Fault_Sites=['tb.dut.subunit_c.U27.A'])
        ]

        # Manually resolve the fault equivalences
        expected_faults[1].equivalent_faults = 2
        expected_faults[2].equivalent_to = expected_faults[1]
        expected_faults[3].equivalent_faults = 2
        expected_faults[4].equivalent_to = expected_faults[3]
        expected_faults[5].equivalent_faults = 2
        expected_faults[6].equivalent_to = expected_faults[5]
        expected_faults[7].equivalent_faults = 2
        expected_faults[8].equivalent_to = expected_faults[7]

        fault_list = parser.parse(fault_list_sample)

        self.assertEqual(fault_list, expected_faults)

    def test_small_delay_defects_fault_list(self):

        parser = self.get_parser()

        fault_list_sample = r"""
            FaultList TDF {
                <  1> NN F (6.532ns) {PORT "tb.dut.subunit_c.U1528.CI"}
                <  1> ON R (6.423ns) {PORT "tb.dut.subunit_c.U1528.CO"}(* "test1"->PC_IF=00000d1c; "test1"->sim_time="   8905ns"; *)
                      -- R (6.6123ns) {PORT "tb.dut.subunit_c.U28.A"}
                <  1> ON F (5.532ns) {PORT "tb.dut.subunit_c.U1528.CO"}(* "test1"->PC_IF=00000d1c; "test1"->sim_time="   8905ns"; *)
                      -- F (6.532ns) {PORT "tb.dut.subunit_c.U28.A"}
                <  1> ON R (2.232ns) {PORT "tb.dut.subunit_c.U1528.S"}(*  "test1"->PC_IF=00000d1c; "test1"->sim_time="   8905ns"; *)
                      -- R (9.722ns) {PORT "tb.dut.subunit_c.U27.A"}
                <  1> ON F (9.432ns) {PORT "tb.dut.subunit_c.U1528.S"}(*  "test1"->PC_IF=00000d1c; "test1"->sim_time="   8905ns"; *)
                      -- F (1.532ns) {PORT "tb.dut.subunit_c.U27.A"}
                      -- ~ (6,4,26) {FLOP "tb.dut.subunit_d.reg_q[0]"}
            }
        """

        fault_list = parser.parse(fault_list_sample)

        expected_faults = [
            zoix.Fault(Fault_Status='NN', Fault_Type='F', Timing_Info=['6.532ns'], Fault_Sites=['tb.dut.subunit_c.U1528.CI']),
            zoix.Fault(Fault_Status='ON', Fault_Type='R', Timing_Info=['6.423ns'], Fault_Sites=['tb.dut.subunit_c.U1528.CO'], Fault_Attributes={'PC_IF': '00000d1c', 'sim_time': '8905ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='R', Timing_Info=['6.6123ns'], Fault_Sites=['tb.dut.subunit_c.U28.A']),
            zoix.Fault(Fault_Status='ON', Fault_Type='F', Timing_Info=['5.532ns'], Fault_Sites=['tb.dut.subunit_c.U1528.CO'], Fault_Attributes={'PC_IF': '00000d1c', 'sim_time': '8905ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='F', Timing_Info=['6.532ns'], Fault_Sites=['tb.dut.subunit_c.U28.A']),
            zoix.Fault(Fault_Status='ON', Fault_Type='R', Timing_Info=['2.232ns'], Fault_Sites=['tb.dut.subunit_c.U1528.S'], Fault_Attributes={'PC_IF': '00000d1c', 'sim_time': '8905ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='R', Timing_Info=['9.722ns'], Fault_Sites=['tb.dut.subunit_c.U27.A']),
            zoix.Fault(Fault_Status='ON', Fault_Type='F', Timing_Info=['9.432ns'], Fault_Sites=['tb.dut.subunit_c.U1528.S'], Fault_Attributes={'PC_IF': '00000d1c', 'sim_time': '8905ns'}),
            zoix.Fault(Fault_Status='ON', Fault_Type='F', Timing_Info=['1.532ns'], Fault_Sites=['tb.dut.subunit_c.U27.A']),
            zoix.Fault(Fault_Status='ON', Fault_Type='~', Timing_Info=['6', '4', '26'], Fault_Sites=['tb.dut.subunit_d.reg_q[0]'])

        ]

        # Manually resolve the fault equivalences
        expected_faults[1].equivalent_faults = 2
        expected_faults[2].equivalent_to = expected_faults[1]
        expected_faults[3].equivalent_faults = 2
        expected_faults[4].equivalent_to = expected_faults[3]
        expected_faults[5].equivalent_faults = 2
        expected_faults[6].equivalent_to = expected_faults[5]
        expected_faults[7].equivalent_faults = 3
        expected_faults[8].equivalent_to = expected_faults[7]
        expected_faults[9].equivalent_to = expected_faults[7]

        self.assertEqual(fault_list, expected_faults)

class TraceTransformerCV32E40PTest(unittest.TestCase):

    grammar = open("../testcrush/grammars/trace_cv32e40p.lark").read()

    def get_parser(self):

        return lark.Lark(grammar=self.grammar, start="start", parser="lalr", transformer=transformers.TraceTransformerCV32E40P())

    def test_doc_example(self):

        parser = self.get_parser()

        trace_sample = r"""Time          Cycle      PC       Instr    Decoded instruction Register and memory contents
130         61 00000150 4481     c.li    x9,0        x9=0x00000000
132         62 00000152 00008437 lui     x8,0x8      x8=0x00008000
134         63 00000156 fff40413 addi    x8,x8,-1    x8:0x00008000  x8=0x00007fff
136         64 0000015a 8c65     c.and   x8,x9       x8:0x00007fff  x9:0x00000000  x8=0x00000000
142         67 0000015c c622     c.swsp  x8,12(x2)   x2:0x00002000  x8:0x00000000 PA:0x0000200c store:0x00000000  load:0xffffffff
"""
        csv_lines = parser.parse(trace_sample)

        expected_csv_lines = ['Time,Cycle,PC,Instr,Decoded instruction,Register and memory contents',
                              '130,61,00000150,4481,"c.li x9,0","x9=0x00000000"',
                              '132,62,00000152,00008437,"lui x8,0x8","x8=0x00008000"',
                              '134,63,00000156,fff40413,"addi x8,x8,-1","x8:0x00008000, x8=0x00007fff"',
                              '136,64,0000015a,8c65,"c.and x8,x9","x8:0x00007fff, x9:0x00000000, x8=0x00000000"',
                              '142,67,0000015c,c622,"c.swsp x8,12(x2)","x2:0x00002000, x8:0x00000000, PA:0x0000200c, store:0x00000000, load:0xffffffff"']

        self.assertEqual(csv_lines, expected_csv_lines)

    def test_no_reg_and_mem_segment(self):

        parser = self.get_parser()

        trace_sample = r"""Time    Cycle   PC  Instr   Decoded instruction Register and memory contents
    905ns              86 00000e36 00a005b3 c.add            x11,  x0, x10       x11=00000e5c x10:00000e5c
    915ns              87 00000e38 00000693 c.addi           x13,  x0, 0         x13=00000000
    925ns              88 00000e3a 00000613 c.addi           x12,  x0, 0
    935ns              89 00000e3c 00000513 c.addi           x10,  x0, 0
    945ns              90 00000e3e 2b40006f c.jal             x0, 692
    975ns              93 000010f2 0d01a703 lw               x14, 208(x3)        x14=00002b20  x3:00003288  PA:00003358
    985ns              94 000010f6 00a00333 c.add             x6,  x0, x10        x6=00000000 x10:00000000
    995ns              95 000010f8 14872783 lw               x15, 328(x14)       x15=00000000 x14:00002b20  PA:00002c68
   1015ns              97 000010fc 00079563 c.bne            x15,  x0, 10        x15:00000000
"""
        csv_lines = parser.parse(trace_sample)

        expected_csv_lines = ['Time,Cycle,PC,Instr,Decoded instruction,Register and memory contents',
                              '905ns,86,00000e36,00a005b3,"c.add x11, x0, x10","x11=00000e5c, x10:00000e5c"',
                              '915ns,87,00000e38,00000693,"c.addi x13, x0, 0","x13=00000000"',
                              '925ns,88,00000e3a,00000613,"c.addi x12, x0, 0"',
                              '935ns,89,00000e3c,00000513,"c.addi x10, x0, 0"',
                              '945ns,90,00000e3e,2b40006f,"c.jal x0, 692"',
                              '975ns,93,000010f2,0d01a703,"lw x14, 208(x3)","x14=00002b20, x3:00003288, PA:00003358"',
                              '985ns,94,000010f6,00a00333,"c.add x6, x0, x10","x6=00000000, x10:00000000"',
                              '995ns,95,000010f8,14872783,"lw x15, 328(x14)","x15=00000000, x14:00002b20, PA:00002c68"',
                              '1015ns,97,000010fc,00079563,"c.bne x15, x0, 10","x15:00000000"']

        self.assertEqual(csv_lines, expected_csv_lines)

    def test_no_operands_in_decoded_instruction_and_no_reg_and_mem(self):

        parser = self.get_parser()

        trace_sample = r"""Time    Cycle   PC  Instr   Decoded instruction Register and memory contents
    905ns              86 00000e36 00a005b3 c.add                   x11=00000e5c x10:00000e5c
    915ns              87 00000e38 00000693 c.addi                  x13=00000000
    925ns              88 00000e3a 00000613 c.addi
    935ns              89 00000e3c 00000513 c.addi           x10,  x0, 0
    945ns              90 00000e3e 2b40006f c.jal             x0, 692
    975ns              93 000010f2 0d01a703 lw               x14, 208(x3)        x14=00002b20  x3:00003288  PA:00003358
    985ns              94 000010f6 00a00333 c.add             x6,  x0, x10        x6=00000000 x10:00000000
    995ns              95 000010f8 14872783 lw               x15, 328(x14)       x15=00000000 x14:00002b20  PA:00002c68
   1015ns              97 000010fc 00079563 c.bne            x15,  x0, 10        x15:00000000
"""
        csv_lines = parser.parse(trace_sample)

        expected_csv_lines = ['Time,Cycle,PC,Instr,Decoded instruction,Register and memory contents',
                              '905ns,86,00000e36,00a005b3,"c.add","x11=00000e5c, x10:00000e5c"',
                              '915ns,87,00000e38,00000693,"c.addi","x13=00000000"',
                              '925ns,88,00000e3a,00000613,"c.addi"',
                              '935ns,89,00000e3c,00000513,"c.addi x10, x0, 0"',
                              '945ns,90,00000e3e,2b40006f,"c.jal x0, 692"',
                              '975ns,93,000010f2,0d01a703,"lw x14, 208(x3)","x14=00002b20, x3:00003288, PA:00003358"',
                              '985ns,94,000010f6,00a00333,"c.add x6, x0, x10","x6=00000000, x10:00000000"',
                              '995ns,95,000010f8,14872783,"lw x15, 328(x14)","x15=00000000, x14:00002b20, PA:00002c68"',
                              '1015ns,97,000010fc,00079563,"c.bne x15, x0, 10","x15:00000000"']

        self.assertEqual(csv_lines, expected_csv_lines)
