====================
Grammars and Parsing
====================

In order to process arbitrarily formated textual information, we resort to EBNF grammars and parsing. To achieve that,
we depend on `Lark <https://lark-parser.readthedocs.io/en/latest/>`_. The structure of the ``grammar`` directory is the
following. Each ``*.lark`` file nests a Lark-compliant grammar. We differentiate between two types of grammars. 

   1. Grammars related to segments of the textual fault report (rpt) of zoix, which are prefixed with ``frpt_``
   2. Grammars related to traces, which are prefixed with ``trace_``

Each grammar must have its corresponding ``Transformer`` to traverse the AST and generate data structures. Specifically for the trace
related grammars, what is expected from the transformer is to transform the AST into a CSV-ready format as a list of strings. 

Whenever a new grammar is added with its corresponding transformer in the ``transformers.py`` the corresponding factories mush be updated
accordingly.

.. automodule:: grammars.transformers
   :members:
   :undoc-members:
   :show-inheritance:
