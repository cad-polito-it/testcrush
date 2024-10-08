#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import lark

from typing import Literal, Any, Iterable
from testcrush.zoix import Fault
from testcrush.utils import get_logger

log = get_logger()


class FaultListTransformer(lark.Transformer):
    """
    This class is expected to act on the grammar defined for the ``FaultList`` segment of a Z01X txt fault report.

    After parsing the segment is returning a list of ``zoix.Fault`` objects with the following attributes:

    - Fault_Status (str): 2-uppercase-letter status
    - Fault_Type (str): 0|1|R|F|~
    - Timing_Info (list[str]): A list with all timing info (if present) e.g., ['6.532ns']
    - Fault_Sites (list[str]): A list of fault sites represented as strings
    - Fault_Attributes (dict[str, str]): A dictionary with all fault attributes (if present)
    """

    _prev_fstatus: str = ""
    _prev_prime: Fault = None
    _is_prime: bool = False


    @staticmethod
    def filter_out_discards(container: Iterable) -> filter:

        return filter(lambda x: x is not lark.Discard, container)

    def start(self, faults: list[Fault]) -> list[Fault]:
        """
        Parsing is finished. The fault list has been generated.
        """

        faults = list(self.filter_out_discards(faults))

        return faults

    def optional_name(self, fault_list_name: str) -> lark.visitors._DiscardType:
        """
        Discard the name of the fault list.

        .. highlight:: python
        .. code-block:: python

            FaultList SomeCNAMEfaultListName {
                      ^^^^^^^^^^^^^^^^^^^^^^
                           discarded
        """
        log.debug(f"Discarding Fault List Name: {str(fault_list_name)}")
        return lark.Discard

    def fault(self, fault_parts: list[tuple[str, Any]]) -> Fault:
        """
        Returns a ``Fault`` object for each line in the FaultList section.

        In this part of the AST all fault information has been parsed and
        all information needed to represent a fault is available.

        .. highlight:: python
        .. code-block:: python

            < 1 1 1> ON 1 { PORT "tb_top.dut.subunit_a.cell.port" } (* "test"->attr=val; *)
                     |   \\       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^               ^^^^^^^^
            Fault Status  \\      Fault Sites (list)               Fault Attributes (dict)
                         Fault Type

        Args:
            fault_parts (list): A list of tuples which hold all information needed to represent a fault.

        Returns:
            Fault: A Fault object whose attributes are:
            - Fault_Status: str
            - Fault_Type: str
            - Fault_Sites: list[str]
            - Fault_Attributes: dict[str, str]
        """
        fault_parts = list(self.filter_out_discards(fault_parts))

        # Resolve fault equivalences.
        if not self._is_prime:

            self._prev_prime.equivalent_faults += 1
            fault = Fault(**dict(fault_parts))
            fault.set("equivalent_to", self._prev_prime)

        else:

            fault = Fault(**dict(fault_parts))

            # Reset the flag
            self._is_prime = False
            # Update the previous prime pointer
            self._prev_prime = fault

        log.debug(repr(Fault(**dict(fault_parts))))
        return fault

    def fault_info(self, args) -> lark.visitors._DiscardType:
        """
        Consumes the fault info segment of a line (if present) and discards it.

        .. highlight:: python
        .. code-block:: python

            < 1 1 1> ON 1 { PORT "tb_top.dut.subunit_a.cell.port" }
             ^^^^^^
            discarded
        """
        log.debug(f"Discarding Fault Info Segment: < {' '.join([str(x) for x in args])} >")
        return lark.Discard

    @lark.v_args(inline=True)
    def fault_status(self, fault_status: str) -> tuple[Literal["Fault Status"], str]:
        """
        Consumes the 2-letter fault status attribute of a line.

        .. highlight:: python
        .. code-block:: python

            < 1 1 1> ON 1 { PORT "tb_top.dut.subunit_a.cell.port" }
                     ^^
                  consumed
        """

        # The -- status is used  to mark  a
        # fault as functionally  equivalent
        # to a prime fault which was listed
        # somewhere above. This means  that
        # it has been already parsed. Hence
        # we use a class variable to always
        # point to the current prime fault.
        # This variable is updated  when  a
        # new prime fault is encountered.

        fault_status = str(fault_status)

        if fault_status == "--":
            fault_status = self._prev_fstatus
        else:
            self._is_prime = True
            self._prev_fstatus = fault_status

        log.debug(f"Returning Fault Status: {fault_status}")

        return ("Fault Status", fault_status)

    @lark.v_args(inline=True)
    def fault_type(self, fault_type: str) -> str:
        """
        Provides the fault type attribute of a line.

        .. highlight:: python
        .. code-block:: python

            < 1 1 1> ON 1 { PORT "tb_top.dut.subunit_a.cell.port" }
                        ^
                     consumed
        """
        log.debug(f"Returning Fault Type: {fault_type}")
        return ("Fault Type", str(fault_type))

    def timing_info(self, timings: list[str]) -> tuple[Literal["Timing Info"], list[str]]:
        """
        Takes all timing info (if present) and returns it as a list of the string-ified tokens.

        .. highlight:: python
        .. code-block:: python
            <  1> NN R (7.52ns) {FLOP "tb_top.dut.subunit_a.cell.port1"}
                        ^^^^^^
                        consumed
        """
        log.debug(f"Passing Received Timing Info {timings}")
        return ("Timing Info", [str(x) for x in timings])

    def location_info(self, sites: list[str]) -> tuple[Literal['Fault Sites'], list[str]]:
        """
        Provides the fault site's hierarhical path from each parsed line as a list of strings.

        .. highlight:: python
        .. code-block:: python

            < 1 1 1> ON 1 { PORT "tb_top.dut.subunit_a.cell.port1" } + { PORT "tb_top.dut.subunit_a.cell.port2" }
                            ^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^        ^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                           ignored       consumed                      ignored       consumed
        """

        log.debug(f"Passing Received Fault Sites in a List {sites}")
        return ("Fault Sites", sites)

    @lark.v_args(inline=True)
    def loc_and_site(self, fault_site: str) -> str:
        """
        Provides the fault site's hierarhical path from each parsed line.

        .. highlight:: python
        .. code-block:: python

            < 1 1 1> ON 1 { PORT "tb_top.dut.subunit_a.cell.port" }
                            ^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                           ignored       consumed
        """
        fault_site = fault_site.strip('"')
        log.debug(f"Returning Fault Site: {fault_site}")
        return fault_site

    def attributes(self, attributes: list[tuple[str, str]]) -> tuple[Literal["Fault Attributes"], dict[str, str]]:
        """
        Provides attributes (if present) of a prime fault as a list of tuples.
        Each tuple holds the attribute name and the corresponding attribute value.

        .. highlight:: python
        .. code-block:: python

            < 1 1 1> ON 1 { PORT "tb_top.dut.subunit_a.cell.port" } (* "testname"->attr_a=12345; "testname"->attr_b=0xA)
                                                                        ^^^^^^^^   ^^^^^^ ^^^^^   ^^^^^^^^  ^^^^^^^ ^^^
                                                                        ignored      consumed      ignored    consumed
        """

        log.debug(f"Passing Received Fault Attributes in a List {attributes}")
        return ("Fault Attributes", dict(attributes))

    @lark.v_args(inline=True)
    def attribute_and_value(self, attribute_name: str, attribute_value: str) -> tuple[str, str]:
        """
        Provides a single attribute (if present) of a prime fault as a tuple.
        The tuple holds the attribute name and the corresponding attribute value.

        .. highlight:: python
        .. code-block:: python

            < 1 1 1> ON 1 { PORT "tb_top.dut.subunit_a.cell.port" } (* "testname"->attr_a=12345; "testname"->attr_b=0xA)
                                                                        ^^^^^^^^   ^^^^^^ ^^^^^
                                                                        ignored      consumed
        """

        log.debug(f"Returning ({attribute_name}, {attribute_value}) pair.")
        return (str(attribute_name), str(attribute_value))


class TraceTransformerCV32E40P(lark.Transformer):
    """
    Transformer for the grammar of the tracer of CV32E40P.

    When applied, returns the trace as a list of strings. The string at index 0
    is the header and the rest the trace entries. Intended for converting the
    textual trace format to CSV.

    More information about the CV32E40P tracer format `here. <https://cv32e40p.readthedocs.io/en/latest/tracer.html>`_
    """

    def start(self, header_and_entries: list[str]) -> list[str]:
        """
        Parsing is finished. Accepts the trace as a list of strings and returns it as-is.
        """
        return header_and_entries

    @lark.v_args(inline=True)
    def header(self, *fields: lark.lexer.Token) -> str:
        """
        Handles the header line of the trace.

        .. highlight:: python
        .. code-block:: python

            Time          Cycle      PC       Instr    Decoded instruction Register and memory contents
            ^^^^          ^^^^^      ^^       ^^^^^    ^^^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            captured     captured  captured  captured  captured            captured
        """
        return ','.join([str(field).strip() for field in fields])

    @lark.v_args(inline=True)
    def entries(self, time: lark.lexer.Token, cycle: lark.lexer.Token, pc: lark.lexer.Token, instr: lark.lexer.Token,
                decoded_instr: lark.lexer.Token, reg_and_mem: lark.lexer.Token | None = None) -> str:
        """
        Processes a single entry line and returns it as a csv-ready string.

        .. highlight:: python
        .. code-block:: python

            142  67 0000015c c622 c.swsp  x8,12(x2) x2:0x00002000 x8:0x00000000 PA:0x0000200c store:0x0 load:0xffffffff
            ^^^  ^^ ^^^^^^^^ ^^^^ ^^^^^^  ^^^^^^^^^ ^^^^^^^^^^^^^ ^^^^^^^^^^^^^ ^^^^^^^^^^^^^ ^^^^^^^^^ ^^^^^^^^^^^^^^^
            Time Cycle  PC   Instr Decoded Instr.   Register and memory contents
        """
        # Remove inline whitespace from string
        decoded_instr = f"\"{' '.join([ word.strip() for word in decoded_instr.split() if word ])}\""

        # Upcast Tokens to str
        entry = list(map(str, [time, cycle, pc, instr]))
        entry.append(decoded_instr)

        if reg_and_mem:
            entry.append(reg_and_mem)

        return ','.join(entry)

    @lark.v_args(inline=True)
    def reg_and_mem(self, *reg_val_pairs: str) -> str:
        """
        Processes a **single** 'Register and memory contents' entry (if present in the trace line).

        .. highlight:: python
        .. code-block:: python

            x2:0x00002000 x8:0x00000000 PA:0x0000200c store:0x0 load:0xffffffff
            ^^^^^^^^^^^^^ ^^^^^^^^^^^^^ ^^^^^^^^^^^^^ ^^^^^^^^^ ^^^^^^^^^^^^^^^
        """
        reg_and_mem = f"\"{', '.join([ str(pair).strip() for pair in reg_val_pairs])}\""
        return reg_and_mem

if __name__ == "__main__":

    # Get the original STL statistics
    parser = lark.Lark(grammar=open("fault_list.lark").read(),
                       start="start",
                       parser="lalr",
                       transformer=FaultListTransformer())
    fault_list = parser.parse(open("../../../sandbox/logfiles/test_primes.rpt").read())
    for fault in fault_list:
        print(repr(fault), f"{'prime' if fault.is_prime() else 'equivalent'}")
    exit(0)
    pc_vals = []
    time_stamps = []

    for fault in fault_list:

        if hasattr(fault, "Fault_Attributes"):

            pc_vals.append(fault.Fault_Attributes["PC_ID"])
            time_stamps.append(fault.Fault_Attributes["sim_time"])

    from collections import Counter

    ccs = Counter(pc_vals)
    ccs_times = Counter(time_stamps)

    parser = lark.Lark(grammar=open("trace_cv32e40p.lark").read(),
                       start="start",
                       parser="lalr",
                       transformer=TraceTransformerCV32E40P())
    # trace_core_00000000.log

    tracetext = parser.parse(open("../../../sandbox/logfiles/trace_core_00000000.log").read())

    print(ccs)
    print(ccs_times)
