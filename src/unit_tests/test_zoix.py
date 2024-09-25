#!/usr/bin/python3

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

class CSVFaultReportTest(unittest.TestCase):

    def test_constructor(self):

        test_obj = zoix.CSVFaultReport(pathlib.Path("mock_fault_summary"), pathlib.Path("mock_fault_report"))
        self.assertEqual(test_obj.fault_summary, pathlib.Path("mock_fault_summary").absolute())
        self.assertEqual(test_obj.fault_report, pathlib.Path("mock_fault_report").absolute())

    def test_set_fault_summary(self):

        test_obj = zoix.CSVFaultReport(pathlib.Path("mock_fault_summary"), pathlib.Path("mock_fault_report"))

        with self.assertRaises(FileExistsError) as cm:

            test_obj.set_fault_summary("new_mock_summary")

        self.assertEqual(str(cm.exception), f"fault_summary='new_mock_summary' does not exist!")

        with mock.patch("pathlib.Path.exists", return_value = True):

            test_obj.set_fault_summary("new_mock_summary")

            self.assertEqual(test_obj.fault_summary, pathlib.Path("new_mock_summary").absolute())

    def test_set_fault_report(self):

        test_obj = zoix.CSVFaultReport(pathlib.Path("mock_fault_summary"), pathlib.Path("mock_fault_report"))

        with self.assertRaises(FileExistsError) as cm:

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
            #print(report)
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
