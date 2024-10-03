#!/usr/bin/python3
# SPDX-License-Identifier: MIT

try:

    from testcrush import config

except ModuleNotFoundError:

    import sys
    sys.path.append("..")
    from testcrush import config

import unittest
import unittest.mock as mock
import pathlib
import re
import toml

class ConfigTest(unittest.TestCase):

    TOML_RAW = r"""
[user_defines]
###########################
# Custom Definitions      #
###########################
sbst_dir = "../../cv32e40p/sbst"
test_dir = "../../cv32e40p/sbst/tests"
root_dir = "../../cv32e40p"
run_dir = "../../cv32e40p/run/vc-z01x"

[isa]
###########################
# ISALANG Location        #
###########################
isa_file = '../../langs/riscv.isa'

[assembly_sources]
###########################
# STL Sources             #
###########################
sources = [
  '%test_dir%/test1.S',
  '%test_dir%/patterns_base.s',
]

[cross_compilation]
###########################
# Cross Compilation       #
###########################
instructions = [
  'make -C %sbst_dir% clean',
  'make -C %sbst_dir% all'
]

[vcs_hdl_compilation]
###########################
# HDL Sources Compilation #
###########################
instructions = []

[vcs_logic_simulation]
###########################
# Logic Simulation (lsim) #
###########################
instructions = [
  'make -C  %root_dir% vcs/sim/gate/shell'
]

[vcs_logic_simulation_control]
###########################
# Lsim configurations     #
###########################

timeout = 60.0
simulation_ok_regex = 'EXIT\sSUCCESS'
test_application_time_regex = 'test application time = ([0-9]+)'
test_application_time_regex_group_no = 1

[zoix_fault_simulation]
###########################
# Fault Simulation (fsim) #
###########################
instructions = [
  'make -C %root_dir% vcs/fgen/saf',
  'make -C %root_dir% vcs/fsim/gate/shell'
]

[zoix_fault_simulation_control]
###########################
# Fsim configurations     #
###########################
timeout = 360.0
allow_regexs = ['Info: Connected to started server']

[fault_simulation_csv_report]
###########################
# CSV fsim files          #
###########################
fsim_fault_summary = '%run_dir%/fsim_out_csv_files/DEFAULT_summary.csv'
fsim_fault_report = '%run_dir%/fsim_out_csv_files/DEFAULT_faultlist.csv'

[coverage]
###########################
# Coverage                #
###########################
sff_config = '%root_dir%/fsim/config.sff'
coverage_formula = '(DD + DN)/(NA + DA + DN + DD + SU)'
fault_status_attribute = 'Status'
# Mutually Exclussive with the ones above #
coverage_summary_col = ''
coverage_summary_row = ''
"""

    def test_replace_toml_placeholders(self):

        defines = {"foo" : "bar",
                   "bee" : "bop"}

        original_dict = {
            "entry1" : r"%foo%/bar",
            "entry2" : [r"blitzkrieg_%bee%", r"%foo%k"],
            "entry3" : { r"a" : r"%foo%", r"b": r"%bee%"}
        }

        expected_dict = {
            "entry1": r"bar/bar",
            "entry2": [r"blitzkrieg_bop", r"bark"],
            "entry3": {r"a": r"bar", r"b": r"bop"}
        }
        new_dict = config.replace_toml_placeholders(original_dict, defines)

        self.assertEqual(expected_dict, new_dict)

    def test_replace_toml_regex(self):

        original_dict = {"some_regex" : r"[a-zA-Z]+",
                         "some_regexs": [r"[0-9]{2}", r"this must be captured"],
                         "some_other_field": 123}


        expected_dict = {
            "some_regex": re.compile(r"[a-zA-Z]+", re.DOTALL),
            "some_regexs": [re.compile(r"[0-9]{2}", re.DOTALL), re.compile(r"this must be captured", re.DOTALL)],
            "some_other_field": 123
        }

        new_dict = config.replace_toml_regex(original_dict)

        self.assertEqual(expected_dict, new_dict)

    def test_sanitize_a0_configuration(self):

        correct_toml_config = self.TOML_RAW

        with mock.patch("io.open", mock.mock_open(read_data=correct_toml_config)) as mocked_open:

            _config = config.sanitize_a0_configuration("some_mocked_file")

        missing_section = r"""
[isa]
###########################
# ISALANG Location        #
###########################
isa_file = '../../langs/riscv.isa'
        """
        with mock.patch("io.open", mock.mock_open(read_data=missing_section)) as mocked_open:

            with self.assertRaises(KeyError) as cm:
                _config = config.sanitize_a0_configuration("some_mocked_file")


        wrong_section_key = r"""
[isa]
###########################
# ISALANG Location        #
###########################
isa_ = '../../langs/riscv.isa'
        """
        with mock.patch("io.open", mock.mock_open(read_data=wrong_section_key)) as mocked_open:

            with self.assertRaises(KeyError) as cm:
                _config = config.sanitize_a0_configuration("some_mocked_file")


    def test_parse_a0_configuration(self):

        with mock.patch("io.open", mock.mock_open(read_data=self.TOML_RAW)) as mocked_open:

            isa, asm, settings = config.parse_a0_configuration("some_mocked_file")

        self.assertEqual(isa, "../../langs/riscv.isa")
        self.assertEqual(asm, ['../../cv32e40p/sbst/tests/test1.S',
                                '../../cv32e40p/sbst/tests/patterns_base.s'])

        self.assertEqual(settings, {'assembly_compilation_instructions': ['make -C ../../cv32e40p/sbst clean',
                                                                           'make -C ../../cv32e40p/sbst all'],
                                     'vcs_compilation_instructions': None,
                                     'vcs_logic_simulation_instructions': ['make -C  ../../cv32e40p vcs/sim/gate/shell'],
                                     'vcs_logic_simulation_control': {'timeout': 60.0,
                                                                      'simulation_ok_regex': re.compile('EXIT\\sSUCCESS', re.DOTALL),
                                                                      'test_application_time_regex': re.compile('test application time = ([0-9]+)', re.DOTALL),
                                                                      'test_application_time_regex_group_no': 1},
                                     'zoix_fault_simulation_instructions': ['make -C ../../cv32e40p vcs/fgen/saf',
                                                                            'make -C ../../cv32e40p vcs/fsim/gate/shell'],
                                     'zoix_fault_simulation_control': {'timeout': 360.0,
                                                                       'allow_regexs': [re.compile('Info: Connected to started server', re.DOTALL)]},
                                     'csv_fault_summary': '../../cv32e40p/run/vc-z01x/fsim_out_csv_files/DEFAULT_summary.csv',
                                     'csv_fault_report': '../../cv32e40p/run/vc-z01x/fsim_out_csv_files/DEFAULT_faultlist.csv',
                                     'coverage_formula': '(DD + DN)/(NA + DA + DN + DD + SU)',
                                     'sff_config': '../../cv32e40p/fsim/config.sff',
                                     'fault_status_attribute': 'Status',
                                     'coverage_summary_row': None,
                                     'coverage_summary_col': None})
