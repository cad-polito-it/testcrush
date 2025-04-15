#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import argparse
import pathlib

from testcrush import config
from testcrush import utils
from testcrush import a0
from testcrush import a1xx

log = utils.get_logger()


def execute_a0(configuration: pathlib.Path):

    ISA, asm_src, a0_settings, a0_preprocessor_settings = config.parse_a0_configuration(configuration)

    A0 = a0.A0(pathlib.Path(ISA), asm_src, a0_settings)

    # 1. Initial run for original STL for TaT and Coverage computation
    init_tat, init_cov = A0.pre_run()
    log.info(f"Initial STL stats are: TaT = {init_tat}, Coverage = {init_cov}.")

    if a0_preprocessor_settings["enabled"]:
        log.info("Preprocessor phase:")

        # This is after pre_run, which means that the fault list
        # has been computed for the golden run and is available.
        preprocessor = a0.PreprocessorA0(A0.fsim_report.fault_list, **a0_preprocessor_settings)

        before_preprocessing = len(A0.all_instructions)
        preprocessor.prune_candidates(A0.all_instructions, A0.path_to_id)
        after_preprocessing = len(A0.all_instructions)
        percentage = round(((before_preprocessing - after_preprocessing) / before_preprocessing) * 100, 4)

        log.info(f"""Preprocessor finished, from {before_preprocessing} to {after_preprocessing} lines.
                 Search space reduced by {percentage}%.""")

    else:
        log.info("Preprocessor phase skipped")

    # 2. Execution of A0
    with utils.Timer():
        A0.run((init_tat, init_cov))

    # 3. Cleanup. Reapping stopped processes.
    A0.post_run()


def execute_a1xx(configuration: pathlib.Path):

    ISA, asm_src, a1xx_settings, a1xx_preprocessor_settings = config.parse_a1xx_configuration(configuration)

    A1xx = a1xx.A1xx(pathlib.Path(ISA), asm_src, a1xx_settings)

    # 1. Initial run for original STL for TaT and Coverage computation
    init_tat, init_cov = A1xx.pre_run()
    log.info(f"Initial STL stats are: TaT = {init_tat}, Coverage = {init_cov}.")

    if a1xx_preprocessor_settings['enabled']:
        log.info("Preprocessor phase:")

        # This is after pre_run, which means that the fault list
        # has been computed for the golden run and is available.
        preprocessor = a1xx.PreprocessorA1xx(A1xx.fsim_report.fault_list, **a1xx_preprocessor_settings)

        before_preprocessing = len(A1xx.all_instructions)
        A1xx.all_code_chunks = preprocessor.prune_candidates(A1xx.all_instructions,
                                                             A1xx.path_to_id,
                                                             a1xx_settings.get("a1xx_segment_dimension"))

        after_preprocessing = len(A1xx.all_instructions)
        percentage = round(((before_preprocessing - after_preprocessing) / before_preprocessing) * 100, 4)

        log.info(f"""Preprocessor finished, from {before_preprocessing} to {after_preprocessing} lines.
                 Search space reduced by {percentage}%.""")

    else:
        log.info("Preprocessor phase skipped")

    # 2. Execution of A1xx
    with utils.Timer():
        A1xx.run((init_tat, init_cov))

    # 3. Cleanup. Reapping stopped processes.
    A1xx.post_run()


def main():

    parser = argparse.ArgumentParser(description="An STL Compaction Toolkit Based on (VC-)Z01X.")

    parser.add_argument("-m", "--compaction_mode", action="store", required=True, choices=["A0", "A1xx"],
                        help="Selection of the compaction algorithm.")
    parser.add_argument("-c", "--configuration", action="store", type=pathlib.Path, required=True,
                        help="TOML configuration file.")
    parser.add_argument("-v", "--verbose", action="count", default=0, required=False,
                        help="Increase verbosity level. Use -v for INFO, -vv for DEBUG, and -vvv for TRACE.")
    parser.add_argument("-l", "--logfile", action="store", default=None, required=False,
                        help="Specify a filename to store all >=DEBUG lvl messages.")

    args = parser.parse_args()

    utils.setup_logger(args.verbose, args.logfile)

    if args.compaction_mode == "A0":
        execute_a0(args.configuration)
    elif args.compaction_mode == "A1xx":
        execute_a1xx(args.configuration)


if __name__ == "__main__":
    main()
