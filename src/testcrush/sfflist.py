#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import lark
import pathlib
import logging

log = logging.getLogger()

FAULT_LIST_GRAMMAR = \
r"""
    start: "FaultList" optional_name? "{" body "}"
    ?optional_name: CNAME

    body: stuck_at_fault+
    #   | transient_fault+

    stuck_at_fault: fault_info?   \
                    fault_status  \
                    fault_type    \
                    location_info \
                    //attributes?

    fault_info: "<" [CNAME | NUMBER]* ">"
    fault_status: FSTATUS
    fault_type: FTYPE

    location_info: _fault_sites_t{loc_and_site, "+"}
    loc_and_site: "{" _LOCTYPE FSITE "}"
    _fault_sites_t{x, sep}: x (sep x)*

    #location_info: locandsite ("+" location_info)*
    //attributes: "(*" CNAME "*)"

    ///////////////
    // TERMINALS //
    ///////////////

    FSTATUS: UCASE_LETTER UCASE_LETTER
           | "--"

    FTYPE: "0"  # stuck-at 0
         | "1"  # stuck-at 1
         | "~"  # bit-flip


    _LOCTYPE: "PORT"
            | "FLOP"
            | "ARRY"
            | "WIRE"
            | "PRIM"
            | "VARI"

    FSITE: /
        "               # Opening quotes
        [\w\.]+         # Any sequence of word characters and dots
        [\[\d+:\d+\]]?  # Optional bit range segment
        "               # Closing quotes
    /x

    %import common.UCASE_LETTER
    %import common.CNAME
    %import common.NUMBER
    %import common.WS
    %ignore WS
"""

class FaultListTransformer(lark.Transformer):

    _prev_fstatus: str = ""

    #@lark.v_args(inline=True)
    def body(self, match: lark.lexer.Token):
        #print('hi from body')
        ...


    def fault_list(self, *args):
        print('hi from fault list')
        print(args)
        return lark.Discard


    def fault_info(self, args: str) -> lark.visitors._DiscardType:
        print(f"Discarding Fault Info Segment: < {' '.join([str(x) for x in args])} >")
        return lark.Discard


    @lark.v_args(inline=True)
    def fault_status(self, fault_status: str) -> str:

        # The -- status is used  to mark  a
        # fault as functionally  equivalent
        # to a prime fault which was listed
        # somewhere above. This means  that
        # it has been already parsed. Hence
        # we use a class variable to always
        # point to the current prime fault.
        # This variable is updated  when  a
        # new prime fault is encountered.

        if fault_status == "--":
            fault_status = self._prev_fstatus
        else:
            self._prev_fstatus = fault_status

        print(f"Returning Fault Status: {fault_status}")

        return fault_status


    @lark.v_args(inline=True)
    def fault_type(self, fault_type: str) -> str:
        print(f"Returning Fault Type: {fault_type}")
        return fault_type

    def location_info(self, sites: list[str]) -> list[str]:
        print(f"Passing Received Fault Sites in a List {sites}")
        return sites


    @lark.v_args(inline=True)
    def loc_and_site(self, fault_site: str) -> tuple[str,str]:
        fault_site = fault_site.strip('"')
        print(f"Returning Fault Site: {fault_site}")
        return fault_site


A = lark.Lark(FAULT_LIST_GRAMMAR, debug=True, parser="lalr", start="start", transformer=FaultListTransformer())

A.parse(r"""
FaultList External {
<  1> ON 1 { PORT "tb_top.wrapper_i.top_i.core_i.load_store_unit_i.U10.A1" }
NA 0 { PORT "system.processor.alu.in1"} + { PORT "system.processor.alu.in5"}
}
""")
