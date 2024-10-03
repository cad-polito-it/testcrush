#!/usr/bin/python3

try:

    from testcrush import transformers
    from testcrush import zoix

except ModuleNotFoundError:

    import sys
    sys.path.append("..")
    from testcrush import transformers
    from testcrush import zoix

import unittest
import unittest.mock as mock
import pathlib
import lark


class FaultListTransformerTest(unittest.TestCase):

    grammar = open("../testcrush/grammars/fault_list.lark").read()

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

        self.assertEqual(fault_list, expected_faults)
