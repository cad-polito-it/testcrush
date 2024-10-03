#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import lark

from typing import Literal, Any, Iterable
from testcrush.zoix import Fault
from testcrush.utils import get_logger

log = get_logger()


class FaultListTransformer(lark.Transformer):

    _prev_fstatus: str = ""

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
            - Fault Type: str
            - Fault Sites: list[str]
            - Fault Attributes: dict[str, str]
        """
        fault_parts = list(self.filter_out_discards(fault_parts))

        log.debug(repr(Fault(**dict(fault_parts))))
        return Fault(**dict(fault_parts))

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
