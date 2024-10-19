#!/usr/bin/python3
# SPDX-License-Identifier: MIT

try:

    from testcrush import zoix

except ModuleNotFoundError:

    import sys
    sys.path.append("..")
    from testcrush import zoix

import unittest
import unittest.mock as mock
import pathlib
import re

class FaultTest(unittest.TestCase):

    def test_constructor_and_equals(self):

        test_obj = zoix.Fault(arbitrary_attr_a = "sa0")
        self.assertEqual(zoix.Fault(arbitrary_attr_a = "sa0"), test_obj)
        self.assertNotEqual(zoix.Fault(arbitrary_attr_b = "sa0"), test_obj)
        self.assertNotEqual(zoix.Fault(arbitrary_attr_a = "sa1"), test_obj)

    def test_repr(self):

        test_obj = zoix.Fault(attr_a = "sa0", attr_b = "detected")
        self.assertEqual(repr(test_obj), "Fault(attr_a='sa0', attr_b='detected')")

    def test_str(self):

        test_obj = zoix.Fault(attr_a = "sa0", attr_b = "detected")
        self.assertEqual(str(test_obj), "attr_a: sa0, attr_b: detected")

    def test_get(self):

        test_obj = zoix.Fault(attr_a = "sa0", attr_b = "detected")
        self.assertEqual(test_obj.get("attr_a"), "sa0")
        self.assertEqual(test_obj.get("attr_c", "Whoops!"), "Whoops!")
        self.assertIsNone(test_obj.get("attr_c"))

    def test_cast_attribute(self):

        test_obj = zoix.Fault(attr_a = "1", attr_b = "detected")
        self.assertIsInstance(test_obj.get("attr_a"), str)
        test_obj.cast_attribute("attr_a", int)
        self.assertIsInstance(test_obj.get("attr_a"), int)

        with self.assertRaises(SystemExit) as cm:

            new_test_obj = zoix.Fault(attr_a = "sa1", attr_b = "detected")
            new_test_obj.cast_attribute("attr_a", int)

class TxtFaultReportTest(unittest.TestCase):
    _fault_report_excerp = r"""
Date("DDDD TTTTT")
User("n.deligiannis")
Tool("REPORT")
Info("  Type:    Fault Coverage Report")
Info(" Version: VERSIONSTR")
Info(" FDB Storage Path: XXXX")
Info(" FDB Server: XXXXX")
Info(" FDB Project: default")
Info(" FDB Campaign: XXXXX")
Info(" Command: fcm::report  -report 'fsim_attr' -showattributes -overwrite -campaign xx -fdb_server XXXX -fdb_project default")

TestList {
    1 test1 {Results:16020 NC:547 NO:101 NN:772 ON:14600}
}

FaultInfo {
    TestNum;
}

StatusDefinitions {
    Redefine DD DX "Redefine DD";
    Redefine PD PX "Redefine PD";
    Redefine ND NX "Redefine ND";
    NN "Not Observed Not Diagnosed";
    NP "Not Observed Potentially Diagnosed";
    PD "Potentially Observed Diagnosed";
    ND "Not Observed Diagnosed";
    PN "Potentially Observed Not Diagnosed";
    PP "Potentially Observed Potentially Diagnosed";
    ON "Observed Not Diagnosed";
    OP "Observed Potentially Diagnosed";
    OD "Observed Diagnosed";
    AN "Assumed Dangerous Not Diagnosed";
    AD "Assumed Dangerous Diagnosed";
    AP "Assumed Dangerous Potentially Diagnosed";
    IS "Invalid Status Promotion";

    DefaultStatus(NN)

    Selected(NA, NN, AN)

    PromotionTable {
        StatusLabels (NN,NP,ND,PD,PN,PP,ON,OP,OD,AP,AN,AD,IS)
        [
            NN NN ND PD PN PP ON OP OD IS IS IS IS ;
            NN NP ND PD PN PP ON OP OD IS IS IS IS ;
            ND ND ND PD PD PD OD OD OD IS IS IS IS ;
            PD PD PD PD PD PD OD OD OD IS IS IS IS ;
            PN PN PD PD PN PP ON ON OD IS IS IS IS ;
            PP PP PD PD PN PP ON OP OD IS IS IS IS ;
            ON ON OD OD ON ON ON ON OD IS IS IS IS ;
            OP OP OD OD ON OP ON OP OD IS IS IS IS ;
            OD OD OD OD OD OD OD OD OD IS IS IS IS ;
            IS IS IS IS IS IS IS IS IS AP AN AD IS ;
            IS IS IS IS IS IS IS IS IS AN AN AD IS ;
            IS IS IS IS IS IS IS IS IS AD AD AD IS ;
            IS IS IS IS IS IS IS IS IS IS IS IS IS ;
        ]
    }

    StatusGroups {
        SA "Safe" (UT, UB, UR, UU);
        SU "Safe Unobserved" (NN, NC, NO, NT);
        DA "Dangerous Assumed" (HA, HM, HT, OA, OZ, IA, IP, IF, IX);
        DN "Dangerous Not Diagnosed" (PN, ON, PP, OP, NP, AN, AP);
        DD "Dangerous Diagnosed" (PD, OD, ND, AD);
    }
}

Coverage {
    "Diagnostic Coverage" = "DD/(NA + DA + DN + DD)";
    "Observational Coverage" = "(DD + DN)/(NA + DA + DN + DD + SU)";
}

FaultList {
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A1"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009bc; "test1"->PC_ID=000009b2; "test1"->PC_IF=000009b6; "test1"->sim_time="   2815ns"; *)
          -- 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U333.Z"}
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A2"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009fc; "test1"->PC_ID=000009f2; "test1"->PC_IF=000009f6; "test1"->sim_time="   6425ns"; *)
    <  1> ON 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.ZN"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009bc; "test1"->PC_ID=000009b2; "test1"->PC_IF=000009b6; "test1"->sim_time="   2815ns"; *)
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.ZN"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009fc; "test1"->PC_ID=000009f2; "test1"->PC_IF=000009f6; "test1"->sim_time="  18745ns"; *)
          -- 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A1"}
          -- 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A2"}
          -- 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U333.Z"}
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U100.A1"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009bc; "test1"->PC_ID=000009b2; "test1"->PC_IF=000009b6; "test1"->sim_time="   7455ns"; *)
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U100.A2"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009bc; "test1"->PC_ID=000009b2; "test1"->PC_IF=000009b6; "test1"->sim_time="   2815ns"; *)
          -- 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U681.A"}
}
#------------------------------------------------------------------------
# Fault Coverage Summary for Default List
#
#                                                  Total
#------------------------------------------------------------------------
# Number of Faults:                                16242 100.00%
#
# Untestable Faults:                                 222   1.37%  100.00%
#   Untestable Unused                        UU      222   1.37%  100.00%
#
# Testable Faults:                                 16020  98.63%  100.00%
#   Not Observed                             NO      101   0.62%    0.63%
#   Not Controlled                           NC      547   3.37%    3.41%
#   Not Observed Not Diagnosed               NN      772   4.75%    4.82%
#   Observed Not Diagnosed                   ON    14600  89.89%   91.14%
#
# Status Groups ---------------------------------------------------------
#   Dangerous Not Diagnosed                  DN    14600  89.89%
#   Safe                                     SA      222   1.37%
#   Safe Unobserved                          SU     1420   8.74%
#
# Coverage --------------------------------------------------------------
#   Diagnostic Coverage                                    0.00%
#   Observational Coverage                                91.14%
#------------------------------------------------------------------------
#------------------------------------------------------------------------
# Attribute Summary for Default List
#
# * Displaying all attributes in FaultList *
#
# Key                      Value                             Count
#------------------------------------------------------------------------
# INSTR                    00000000                           3740
# INSTR                    00005117                              6
# INSTR                    079aa423                             15
# INSTR                    3cb3079a                           5418
# INSTR                    4cb3079a                              9
# INSTR                    4d818193                              8
"""
    def create_object(self):

        real_open = open  # Keep an alias to real open

        with mock.patch("builtins.open", mock.mock_open(read_data=self._fault_report_excerp)) as mocked_open:

            # Careful! the constructor invokes lark parsing which means it opens >1 files
            # However, what we want to patch is just the fault report excerpt and not the
            # rest, e.g., the grammars. Hence, we need to hack our way around this  issue
            # and only patch the open when the fault report is read. Hence this elaborate
            # side effect trick. Note that i am also capturing real_open above, since  at
            # this point, it is already patched.

            def open_side_effect(file, mode="r", *args, **kwargs):

                if isinstance(file, pathlib.Path):
                    file = str(file)

                if file == "mock_fault_report":
                    return mock.mock_open(read_data=self._fault_report_excerp)()
                else:
                    # Use the real open function for grammar parsing
                    return real_open(file, mode, *args, **kwargs)

            # Set the side_effect to handle multiple file paths
            mocked_open.side_effect = open_side_effect

            test_obj = zoix.TxtFaultReport(pathlib.Path("mock_fault_report"))

        return test_obj

    def test_constructor(self):

        test_obj = self.create_object()
        self.assertEqual(test_obj.fault_report, self._fault_report_excerp)
        expected = [zoix.Fault(fault_status='ON', fault_type='1', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A1'], fault_attributes={'INSTR': '3cb3079a', 'INSTR_ADDR': '000009bc', 'PC_ID': '000009b2', 'PC_IF': '000009b6', 'sim_time': '2815ns'}),
                   zoix.Fault(fault_status='ON', fault_type='1', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U333.Z']),
                   zoix.Fault(fault_status='ON', fault_type='1', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A2'], fault_attributes={'INSTR': '3cb3079a', 'INSTR_ADDR': '000009fc', 'PC_ID': '000009f2', 'PC_IF': '000009f6', 'sim_time': '6425ns'}),
                   zoix.Fault(fault_status='ON', fault_type='0', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.ZN'], fault_attributes={'INSTR': '3cb3079a', 'INSTR_ADDR': '000009bc', 'PC_ID': '000009b2', 'PC_IF': '000009b6', 'sim_time': '2815ns'}),
                   zoix.Fault(fault_status='ON', fault_type='1', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.ZN'], fault_attributes={'INSTR': '3cb3079a', 'INSTR_ADDR': '000009fc', 'PC_ID': '000009f2', 'PC_IF': '000009f6', 'sim_time': '18745ns'}),
                   zoix.Fault(fault_status='ON', fault_type='0', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A1']),
                   zoix.Fault(fault_status='ON', fault_type='0', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A2']),
                   zoix.Fault(fault_status='ON', fault_type='0', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U333.Z']),
                   zoix.Fault(fault_status='ON', fault_type='1', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U100.A1'], fault_attributes={'INSTR': '3cb3079a', 'INSTR_ADDR': '000009bc', 'PC_ID': '000009b2', 'PC_IF': '000009b6', 'sim_time': '7455ns'}),
                   zoix.Fault(fault_status='ON', fault_type='1', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U100.A2'], fault_attributes={'INSTR': '3cb3079a', 'INSTR_ADDR': '000009bc', 'PC_ID': '000009b2', 'PC_IF': '000009b6', 'sim_time': '2815ns'}),
                   zoix.Fault(fault_status='ON', fault_type='0', fault_sites=['tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U681.A'])]

        expected[1].equivalent_to = expected[0]
        expected[0].equivalent_faults = 2
        expected[5].equivalent_to = expected[4]
        expected[6].equivalent_to = expected[4]
        expected[7].equivalent_to = expected[4]
        expected[4].equivalent_faults = 4
        expected[10].equivalent_to = expected[9]
        expected[9].equivalent_faults = 2
        self.assertEqual(test_obj.fault_list, expected)

        self.assertEqual(test_obj.status_groups, {'SA': ['UT', 'UB', 'UR', 'UU'],
                                                  'SU': ['NN', 'NC', 'NO', 'NT'],
                                                  'DA': ['HA', 'HM', 'HT', 'OA', 'OZ', 'IA', 'IP', 'IF', 'IX'],
                                                  'DN': ['PN', 'ON', 'PP', 'OP', 'NP', 'AN', 'AP'],
                                                  'DD': ['PD', 'OD', 'ND', 'AD']})

        self.assertEqual(test_obj.coverage, {"Diagnostic Coverage": "DD/(NA + DA + DN + DD)",
                                             "Observational Coverage": "(DD + DN)/(NA + DA + DN + DD + SU)"})

    def test_extract(self):

        test_obj = self.create_object()

        test_list = test_obj.extract("TestList")
        self.assertEqual(test_list, """\
TestList {
    1 test1 {Results:16020 NC:547 NO:101 NN:772 ON:14600}
}""")

        fault_info = test_obj.extract("FaultInfo")
        self.assertEqual(fault_info, """\
FaultInfo {
    TestNum;
}""")

        status_definitions = test_obj.extract("StatusDefinitions")
        self.assertEqual(status_definitions, """\
StatusDefinitions {
    Redefine DD DX "Redefine DD";
    Redefine PD PX "Redefine PD";
    Redefine ND NX "Redefine ND";
    NN "Not Observed Not Diagnosed";
    NP "Not Observed Potentially Diagnosed";
    PD "Potentially Observed Diagnosed";
    ND "Not Observed Diagnosed";
    PN "Potentially Observed Not Diagnosed";
    PP "Potentially Observed Potentially Diagnosed";
    ON "Observed Not Diagnosed";
    OP "Observed Potentially Diagnosed";
    OD "Observed Diagnosed";
    AN "Assumed Dangerous Not Diagnosed";
    AD "Assumed Dangerous Diagnosed";
    AP "Assumed Dangerous Potentially Diagnosed";
    IS "Invalid Status Promotion";
    DefaultStatus(NN)
    Selected(NA, NN, AN)
    PromotionTable {
        StatusLabels (NN,NP,ND,PD,PN,PP,ON,OP,OD,AP,AN,AD,IS)
        [
            NN NN ND PD PN PP ON OP OD IS IS IS IS ;
            NN NP ND PD PN PP ON OP OD IS IS IS IS ;
            ND ND ND PD PD PD OD OD OD IS IS IS IS ;
            PD PD PD PD PD PD OD OD OD IS IS IS IS ;
            PN PN PD PD PN PP ON ON OD IS IS IS IS ;
            PP PP PD PD PN PP ON OP OD IS IS IS IS ;
            ON ON OD OD ON ON ON ON OD IS IS IS IS ;
            OP OP OD OD ON OP ON OP OD IS IS IS IS ;
            OD OD OD OD OD OD OD OD OD IS IS IS IS ;
            IS IS IS IS IS IS IS IS IS AP AN AD IS ;
            IS IS IS IS IS IS IS IS IS AN AN AD IS ;
            IS IS IS IS IS IS IS IS IS AD AD AD IS ;
            IS IS IS IS IS IS IS IS IS IS IS IS IS ;
        ]
    }
    StatusGroups {
        SA "Safe" (UT, UB, UR, UU);
        SU "Safe Unobserved" (NN, NC, NO, NT);
        DA "Dangerous Assumed" (HA, HM, HT, OA, OZ, IA, IP, IF, IX);
        DN "Dangerous Not Diagnosed" (PN, ON, PP, OP, NP, AN, AP);
        DD "Dangerous Diagnosed" (PD, OD, ND, AD);
    }
}""")

        promotion_table = test_obj.extract("PromotionTable")
        self.assertEqual(promotion_table, """\
    PromotionTable {
        StatusLabels (NN,NP,ND,PD,PN,PP,ON,OP,OD,AP,AN,AD,IS)
        [
            NN NN ND PD PN PP ON OP OD IS IS IS IS ;
            NN NP ND PD PN PP ON OP OD IS IS IS IS ;
            ND ND ND PD PD PD OD OD OD IS IS IS IS ;
            PD PD PD PD PD PD OD OD OD IS IS IS IS ;
            PN PN PD PD PN PP ON ON OD IS IS IS IS ;
            PP PP PD PD PN PP ON OP OD IS IS IS IS ;
            ON ON OD OD ON ON ON ON OD IS IS IS IS ;
            OP OP OD OD ON OP ON OP OD IS IS IS IS ;
            OD OD OD OD OD OD OD OD OD IS IS IS IS ;
            IS IS IS IS IS IS IS IS IS AP AN AD IS ;
            IS IS IS IS IS IS IS IS IS AN AN AD IS ;
            IS IS IS IS IS IS IS IS IS AD AD AD IS ;
            IS IS IS IS IS IS IS IS IS IS IS IS IS ;
        ]
    }""")

        status_groups = test_obj.extract("StatusGroups")
        self.assertEqual(status_groups, """\
    StatusGroups {
        SA "Safe" (UT, UB, UR, UU);
        SU "Safe Unobserved" (NN, NC, NO, NT);
        DA "Dangerous Assumed" (HA, HM, HT, OA, OZ, IA, IP, IF, IX);
        DN "Dangerous Not Diagnosed" (PN, ON, PP, OP, NP, AN, AP);
        DD "Dangerous Diagnosed" (PD, OD, ND, AD);
    }""")

        coverage = test_obj.extract("Coverage")
        self.assertEqual(coverage, """\
Coverage {
    "Diagnostic Coverage" = "DD/(NA + DA + DN + DD)";
    "Observational Coverage" = "(DD + DN)/(NA + DA + DN + DD + SU)";
}""")

        fault_list = test_obj.extract("FaultList")
        self.assertEqual(fault_list, """\
FaultList {
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A1"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009bc; "test1"->PC_ID=000009b2; "test1"->PC_IF=000009b6; "test1"->sim_time="   2815ns"; *)
          -- 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U333.Z"}
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A2"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009fc; "test1"->PC_ID=000009f2; "test1"->PC_IF=000009f6; "test1"->sim_time="   6425ns"; *)
    <  1> ON 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.ZN"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009bc; "test1"->PC_ID=000009b2; "test1"->PC_IF=000009b6; "test1"->sim_time="   2815ns"; *)
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.ZN"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009fc; "test1"->PC_ID=000009f2; "test1"->PC_IF=000009f6; "test1"->sim_time="  18745ns"; *)
          -- 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A1"}
          -- 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U10.A2"}
          -- 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U333.Z"}
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U100.A1"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009bc; "test1"->PC_ID=000009b2; "test1"->PC_IF=000009b6; "test1"->sim_time="   7455ns"; *)
    <  1> ON 1 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U100.A2"}(* "test1"->INSTR=3cb3079a; "test1"->INSTR_ADDR=000009bc; "test1"->PC_ID=000009b2; "test1"->PC_IF=000009b6; "test1"->sim_time="   2815ns"; *)
          -- 0 {PORT "tb_top.wrapper_i.top_i.core_i.ex_stage_i.mult_i.U681.A"}
}""")

    def test_compute_coverage(self):
        test_obj = self.create_object()

        coverage = test_obj.compute_coverage()

        self.assertEqual(coverage, {'Diagnostic Coverage': 0.0, 'Observational Coverage': 1.0})



class CSVFaultReportTest(unittest.TestCase):

    def test_constructor(self):

        test_obj = zoix.CSVFaultReport(pathlib.Path("mock_fault_summary"), pathlib.Path("mock_fault_report"))
        self.assertEqual(test_obj.fault_summary, pathlib.Path("mock_fault_summary").absolute())
        self.assertEqual(test_obj.fault_report, pathlib.Path("mock_fault_report").absolute())

    def test_set_fault_summary(self):

        test_obj = zoix.CSVFaultReport(pathlib.Path("mock_fault_summary"), pathlib.Path("mock_fault_report"))

        with self.assertRaises(FileNotFoundError) as cm:

            test_obj.set_fault_summary("new_mock_summary")

        self.assertEqual(str(cm.exception), f"fault_summary='new_mock_summary' does not exist!")

        with mock.patch("pathlib.Path.exists", return_value = True):

            test_obj.set_fault_summary("new_mock_summary")

            self.assertEqual(test_obj.fault_summary, pathlib.Path("new_mock_summary").absolute())

    def test_set_fault_report(self):

        test_obj = zoix.CSVFaultReport(pathlib.Path("mock_fault_summary"), pathlib.Path("mock_fault_report"))

        with self.assertRaises(FileNotFoundError) as cm:

            test_obj.set_fault_report("new_mock_report")

        self.assertEqual(str(cm.exception), f"fault_report='new_mock_report' does not exist!")

        with mock.patch("pathlib.Path.exists", return_value = True):

            test_obj.set_fault_report("new_mock_report")

            self.assertEqual(test_obj.fault_report, pathlib.Path("new_mock_report").absolute())

    def test_extract_summary_cells_from_row(self):

        test_obj = zoix.CSVFaultReport(pathlib.Path("mock_fault_summary"), pathlib.Path("mock_fault_report"))

        with mock.patch("builtins.open", mock.mock_open(read_data="""\
"Category","Name","Label","Prime Cnt","Prime Pct","Prime Sub Pct","Total Cnt","Total Pct","Total Sub Pct"
"General","Number of Faults","",11034,100.00,"",18684,100.00,""
"General","Untestable Faults:","",100,0.91,100.00,100,0.54,100.00
"Fault","Untestable Unused","UU",100,0.91,100.00,100,0.91,100.00
"General","Testable Faults:","",10934,99.09,100.00,18584,99.46,100.00
"Fault","Oscillating Zero","OZ",2,0.02,0.02,4,0.02,0.02
"Fault","Not Observed","NO",672,6.09,6.15,1048,6.09,5.64
"Fault","Not Controlled","NC",550,4.98,5.03,1096,4.98,5.90
"Fault","Not Observed Not Diagnosed","NN",2321,21.03,21.23,3799,21.03,20.44
"Fault","Observed Not Diagnosed","ON",7389,66.97,67.58,12637,66.97,68.00
"Group","Dangerous Assumed","DA",2,0.02,"",4,0.02,""
"Group","Dangerous Not Diagnosed","DN",7389,67.58,"",12637,68.00,""
"Group","Safe","SA",100,0.91,"",100,0.54,""
"Group","Safe Unobserved","SU",3543,32.40,"",5943,31.98,""
"Coverage","Diagnostic Coverage","","","0.00%","","","0.00%",""
"Coverage","Observational Coverage","","","67.58%","","","68.00%",""""")):

            diagnostic_coverage = test_obj.extract_summary_cells_from_row(15,8)
            observationL_coverage = test_obj.extract_summary_cells_from_row(16,8)
            total_faults = test_obj.extract_summary_cells_from_row(2,2,4,7)

            self.assertEqual(diagnostic_coverage, ["0.00%"])
            self.assertEqual(observationL_coverage, ["68.00%"])
            self.assertEqual(total_faults, ["Number of Faults", "11034", "18684"])

            # Row is out of bounds
            with self.assertRaises(SystemExit) as cm:

                test_obj.extract_summary_cells_from_row(20,1)

            self.assertEqual(str(cm.exception), "1")

            # Column is out of bounds
            with self.assertRaises(SystemExit) as cm:

                test_obj.extract_summary_cells_from_row(10,1,20)

            self.assertEqual(str(cm.exception), "1")

    def test_parse_fault_report(self):

        self.maxDiff = None

        test_obj = zoix.CSVFaultReport(pathlib.Path("mock_fault_summary"), pathlib.Path("mock_fault_report"))

        with mock.patch("builtins.open", mock.mock_open(read_data='''\
"FID","Test Name","Prime","Status","Model","Timing","Cycle Injection","Cycle End","Class","Location"
1,"test1","yes","ON","0","","","","PORT","path_to_fault_1.portA"
2,"test1",1,"ON","0","","","","PORT","path_to_fault_2.portB"
3,"test1","yes","ON","1","","","","PORT","path_to_fault_3.portC"''')):

            report = test_obj.parse_fault_report()
            expected_report = [
                zoix.Fault(**{"FID":"1", "Test Name":"test1", "Prime":"yes", "Status":"ON", "Model":"0", "Timing":"", "Cycle Injection":"", "Cycle End":"", "Class":"PORT", "Location":"path_to_fault_1.portA"}),
                zoix.Fault(**{"FID":"2", "Test Name":"test1", "Prime":"1", "Status":"ON", "Model":"0", "Timing":"", "Cycle Injection":"", "Cycle End":"", "Class":"PORT", "Location":"path_to_fault_2.portB"}),
                zoix.Fault(**{"FID":"3", "Test Name":"test1", "Prime":"yes", "Status":"ON", "Model":"1", "Timing":"", "Cycle Injection":"", "Cycle End":"", "Class":"PORT", "Location":"path_to_fault_3.portC"}),
            ]

            self.assertEqual(report, expected_report)


class ZoixInvokerTest(unittest.TestCase):

    def test_execute(self):

        test_obj = zoix.ZoixInvoker()

        with mock.patch("subprocess.Popen.communicate", return_value = ("stdout OK", "stderr OK") ) as mock_popen:

            stdout, stderr = test_obj.execute("echo hello")

            self.assertEqual([stdout, stderr], ["stdout OK", "stderr OK"])

        stdout, stderr = test_obj.execute("for i in $(seq 100000); do echo $i; done", timeout = 0.1)
        self.assertEqual([stdout, stderr], ["TimeoutExpired", "TimeoutExpired"])

    def test_compile_sources(self):

        test_obj = zoix.ZoixInvoker()

        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = ("stdout contains text", "")) as mocked_execute:

            compilation = test_obj.compile_sources("mock_compilation_instruction")

            self.assertEqual(compilation, zoix.Compilation.SUCCESS)

        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = ("stdout contains text", "stderr contains text too!")) as mocked_execute:

            compilation = test_obj.compile_sources("mock_compilation_instruction")

            self.assertEqual(compilation, zoix.Compilation.ERROR)

    def test_logic_simulate(self):

        test_obj = zoix.ZoixInvoker()

        logic_sim_snippet = r"""\
make[1]: Entering directory `redacted'
make[1]: Leaving directory `redacted'
make[1]: Entering directory `redacted'
rm -f _cuarc*.so _csrc*.so pre_vcsobj_*.so share_vcsobj_*.so
if [ -x ../simv ]; then chmod a-x ../simv; fi
g++  -o ../simv -rdynamic  -Wl,-rpath='$ORIGIN'/simv.daidir -Wl,-rpath=./simv.daidir -Wl,-rpath=redacted -L /redacted  \
-Wl,-rpath-link=./  /usr/lib64/libnuma.so.1   \
objs/amcQw_d.o   _153044_archive_1.so objs/udps/fTq4m.o \
objs/udps/nC9PF.o objs/udps/u1p1q.o   SIM_l.o \
rmapats_mop.o rmapats.o rmar.o rmar_nd.o  rmar_llvm_0_1.o rmar_llvm_0_0.o \
-lvirsim -lerrorinf -lsnpsmalloc -lvfs -lvcsnew -lsimprofile -luclinative redacted \
-Wl,-whole-archive  -lvcsucli -Wl,-no-whole-archive  redacted -ldl  -lc -lm -lpthread -ldl
../simv up to date
make[1]: Leaving directory `redacted'
CPU time: 2.597 seconds to compile + .784 seconds to elab + .311 seconds to link
make -C redacted
make[1]: Entering directory `redacted'
/opt/riscv/bin/riscv32-unknown-elf-gcc -march=rv32imc -o sbst.elf -w -Os -g -nostdlib \
        -Xlinker -Map=sbst.map \
        -T link.ld \
        -static \
        crt0.S main.c syscalls.c vectors.S tests/test1.S  \
        -I /opt/riscv/riscv32-unknown-elf/include \
        -L /opt/riscv/riscv32-unknown-elf/lib \
        -lc -lm -lgcc
/opt/riscv/bin/riscv32-unknown-elf-objcopy -O verilog sbst.elf sbst.hex
sed -i 's/@0020/@001C/; s/@0021/@001D/; s/@0022/@001E/; s/@0023/@001F/' sbst.hex
make[1]: Leaving directory `redacted'
cd redacted &&\
./simv +firmware=redacted.hex
Chronologic VCS simulator copyright 1991-2023
Contains Synopsys proprietary information.
Compiler version V-2023.12-SP1_Full64; Runtime version V-2023.12-SP1_Full64;  Aug 28 12:07 2024
EXIT SUCCESS
$finish called from file "redacted", line 155.
[TESTBENCH] 482140ns: test application time = 48209 clock cycles (482090 ns)
$finish at simulation time  482140ns
           V C S   S i m u l a t i o n   R e p o r t
Time: 482140000 ps
CPU Time:      7.710 seconds;       Data structure size:   6.4Mb
Day Month HH:MM:SS YYYY"""

        faulty_lsim_snippet = r"""
cd redacted/testcrush/cv32e40p/run/vcs &&\
./simv +firmware=redacted/testcrush/cv32e40p/sbst/sbst.hex
Info: [VCS_SAVE_RESTORE_INFO] ASLR (Address Space Layout Randomization) is detected on the machine. To enable $save functionality, ASLR will be switched off and simv re-executed.
Please use '-no_save' simv switch to avoid re-execution or '-suppress=ASLR_DETECTED_INFO' to suppress this message.
Chronologic VCS simulator copyright 1991-2023
Contains Synopsys proprietary information.
Compiler version V-2023.12-SP1_Full64; Runtime version V-2023.12-SP1_Full64;  Sep 16 13:14 2024
out of bounds read from 55555600
Fatal: "redacted/testcrush/cv32e40p/example_tb/core/mm_ram.sv", 389: tb_top.wrapper_i.ram_i.read_mux: at time 162880000 ps
$finish called from file "redacted/testcrush/cv32e40p/example_tb/core/mm_ram.sv", line 389.
[TESTBENCH] 162880ns: test application time = 16284 clock cycles (162840 ns)
$finish at simulation time  162880ns
           V C S   S i m u l a t i o n   R e p o r t
Time: 162880000 ps
CPU Time:      4.660 seconds;       Data structure size:   6.4Mb
Day Month HH:MM:SS YYYY
"""
        tat_dict = {
            "simulation_ok_regex": re.compile(r"EXIT\sSUCCESS"),
            "test_application_time_regex": re.compile(r"test application time = ([0-9]+)"),
            "test_application_time_regex_group_no": 1,
            "tat_value": []
        }

        # Simulation Success
        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = (logic_sim_snippet, "")) as mocked_execute:

            self.assertEqual(tat_dict["tat_value"], [])

            logic_simulation = test_obj.logic_simulate("mock_logic_simulation_instruction", **tat_dict)

            self.assertEqual(logic_simulation, zoix.LogicSimulation.SUCCESS)
            # Mutable object [] has been set to value
            self.assertEqual(tat_dict["tat_value"].pop(), 48209)

            # Do not supply a regexp, let the default one work and capture $finish
            del tat_dict["test_application_time_regex"]
            logic_simulation = test_obj.logic_simulate("mock_logic_simulation_instruction", **tat_dict)

            self.assertEqual(logic_simulation, zoix.LogicSimulation.SUCCESS)
            self.assertEqual(tat_dict["tat_value"].pop(), 482140)

        # Simulation Error
        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = (logic_sim_snippet, "stderr has text!")) as mocked_execute:

            logic_simulation = test_obj.logic_simulate("mock_logic_simulation_instruction")
            self.assertEqual(logic_simulation, zoix.LogicSimulation.SIM_ERROR)

        # Stout contains error messages from lsim
        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = (faulty_lsim_snippet, "")) as mocked_execute:

            logic_simulation = test_obj.logic_simulate("mock_logic_simulation_instruction", **tat_dict)
            self.assertEqual(logic_simulation, zoix.LogicSimulation.SIM_ERROR)

        # Simulation Timeout
        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = ("TimeoutExpired", "TimeoutExpired")) as mocked_execute:

            logic_simulation = test_obj.logic_simulate("mock_logic_simulation_instruction")
            self.assertEqual(logic_simulation, zoix.LogicSimulation.TIMEOUT)

    def test_fault_simulate(self):

        test_obj = zoix.ZoixInvoker()

        # FSIM Success
        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = ("Some fault sim text", "")) as mocked_execute:

            fault_simulation = test_obj.fault_simulate("mock_fsim_instruction1", "mock_fsim_instruction2")
            self.assertEqual(fault_simulation, zoix.FaultSimulation.SUCCESS)

        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = ("Some fault sim text", "Stderr text but must be ignored!")) as mocked_execute:

            fault_simulation = test_obj.fault_simulate("mock_fsim_instruction1", "mock_fsim_instruction2",
                                                       allow_regexs = [re.compile(r"Stderr text but must be ignored\!")])
            self.assertEqual(fault_simulation, zoix.FaultSimulation.SUCCESS)

        # FSIM Error
        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = ("Some fault sim text", "Stderr has text!")) as mocked_execute:

            fault_simulation = test_obj.fault_simulate("mock_fsim_instruction1", "mock_fsim_instruction2")
            self.assertEqual(fault_simulation, zoix.FaultSimulation.FSIM_ERROR)

        # FSIM Timeout
        with mock.patch("testcrush.zoix.ZoixInvoker.execute", return_value = ("TimeoutExpired", "TimeoutExpired")) as mocked_execute:

            fault_simulation = test_obj.fault_simulate("mock_fsim_instruction1", "mock_fsim_instruction2", timeout = 1)
            self.assertEqual(fault_simulation, zoix.FaultSimulation.TIMEOUT)
