#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import pathlib
import csv
import sqlite3
import io

import testcrush.grammars.transformers as transformers
from testcrush.utils import get_logger, Singleton
from testcrush import zoix

log = get_logger()


class Preprocessor(metaclass=Singleton):
    """Superclass: Filters out candidate instructions"""

    _trace_db = ".trace.db"

    def __init__(self, fault_list: list[zoix.Fault], **kwargs) -> 'Preprocessor':

        factory = transformers.TraceTransformerFactory()
        parser = factory(kwargs.get("processor_name"))
        processor_trace = kwargs.get("processor_trace")

        with open(processor_trace) as src:
            trace_raw = src.read()

        self.trace = parser.parse(trace_raw)
        self.fault_list: list[zoix.Fault] = fault_list
        self.elf = kwargs.get("elf_file")
        self.zoix2trace = kwargs.get("zoix_to_trace")

        self._create_trace_db()

    def _create_trace_db(self):
        """
        Transforms the trace of the DUT to a SQLite database of a single table. The header of the CSV is mapped to the
        DB column names and then the CSV body is transformed into DB row entries.
        """

        # If pre-existent db is found, delete it.
        db = pathlib.Path(self._trace_db)
        if db.exists():
            log.debug(f"Database {self._trace_db} exists. Overwritting it.")
            db.unlink()

        con = sqlite3.connect(self._trace_db)
        cursor = con.cursor()

        header: list[str] = self.trace[0].split(',')
        header = list(map(lambda column_name: f"\"{column_name}\"", header))
        header = ", ".join(header)

        cursor.execute(f"CREATE TABLE trace({header})")

        body: list[str] = self.trace[1:]

        with io.StringIO('\n'.join(body)) as source:

            for row in csv.reader(source):

                cursor.execute(f"INSERT INTO trace VALUES ({', '.join(['?'] * len(row))})", row)

        con.commit()
        con.close()

        log.debug(f"Database {self._trace_db} created.")

    def query_trace_db(self, select: str, where: dict[str, str],
                       history: int = 5, allow_multiple: bool = False) -> list[tuple[str, ...]]:
        """
        Perform a query with the specified parameters.

        Assuming that the DB looks like this:

        ::

            Time || Cycle || PC       || Instruction
            -----||-------||----------||------------
            10ns || 1     || 00000004 || and
            20ns || 2     || 00000008 || or          <-*
            30ns || 3     || 0000000c || xor         <-|
            40ns || 4     || 00000010 || sll         <-|
            50ns || 5     || 00000014 || j           <-|
            60ns || 6     || 0000004c || addi        <-*
            70ns || 7     || 00000050 || wfi

        And you perform a query for the ``select="PC"`` and ``where={"PC": "0000004c", "Time": "60ns"}`` then the search
        would result in a window of 1+4 ``PC`` values, indicated by ``<-`` in the snapshot above. The size of the window
        defaults to 5 but can be freely selected by the user.

        Args:
            select (str): The field to select in the query.
            where (dict[str, str]): A dictionary specifying conditions to filter the query.
            history (int, optional): The number of past queries to include. Defaults to 5.
            allow_multiple (bool, optional): Whether to allow multiple results. Defaults to False.

        Returns:
            list[tuple[str, ...]: A list of query results (tuples of strings) matching the criteria.
        """

        db = pathlib.Path(self._trace_db)
        if not db.exists():
            raise FileNotFoundError("Trace DB not found")

        columns = where.keys()

        query = f"""
            SELECT ROWID
            FROM trace
            WHERE {' AND '.join([f'{x} = ?' for x in columns])}
        """

        values = where.values()
        with sqlite3.connect(db) as con:

            cursor = con.cursor()

            cursor.execute(query, tuple(values))
            rowids = cursor.fetchall()

            if not rowids:
                raise ValueError(f"No row found for {', '.join([f'{k}={v}' for k, v in where.items()])}")

            if len(rowids) > 1 and not allow_multiple:
                raise ValueError(f"Query resulted in multiple ROWIDs for \
{', '.join([f'{k}={v}' for k, v in where.items()])}")

            result = list()
            for rowid, in rowids:

                query_with_history = f"""
                    SELECT {'"'+select+'"' if select != '*' else select} FROM trace
                    WHERE ROWID <= ?
                    ORDER BY ROWID DESC
                    LIMIT ?
                """

            cursor.execute(query_with_history, (rowid, history))
            result += cursor.fetchall()[::-1]

            return result
