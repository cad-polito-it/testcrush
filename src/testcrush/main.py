#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import argparse
import logging
import pathlib

from testcrush import config
from testcrush import utils
from testcrush import a0


def execute_a0(configuration: pathlib.Path):

    config.sanitize_a0_configuration(configuration)

    A0 = a0.A0(config.parse_a0_configuration(configuration))

    A0.run(A0.pre_run())


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

    trace_level_num = 5
    logging.addLevelName(trace_level_num, "TRACE")

    def trace(self, message, *args, **kws):
        if self.isEnabledFor(trace_level_num):
            self._log(trace_level_num, message, args, **kws)

    logging.Logger.trace = trace

    _v_to_levels = {
        0: logging.NOTSET,
        1: logging.INFO,
        2: logging.DEBUG,
        3: trace_level_num
    }

    utils.setup_logger(_v_to_levels[args.verbose], args.logfile)

    if args.compaction_mode == "A0":
        execute_a0(args.configuration)
    elif args.compaction_mode == "A1xx":
        raise NotImplementedError("The compaction algorithm A1xx is not yet implemented")


if __name__ == "__main__":
    main()
