===========
asm module 
===========

The ``asm.py`` module contains utilities to handle file I/O operations on arbitrary assembly files.
The purpose is to remove and to restore lines from the associated assembly file accurately.

.. toctree::
   :maxdepth: 2
   :caption: Contents

---
ISA
---

This class, which implements the Singleton pattern, is used to parse a 
user-defined `language file <https://github.com/cad-polito-it/testcrush/tree/main/langs>`_ and offers
utilities to check whether an arbitrary string is a valid instruction according to the language file.

.. autoclass:: asm.ISA
   :members:
   :undoc-members:
   :show-inheritance:

--------
Codeline
--------

This is a dataclass to represent a single line of assembly code. Note that the ``lineno`` attribute
which corresponds to the line number of the code line in the assembly file uses **0-based** indexing!

.. autoclass:: asm.Codeline
   :members:
   :undoc-members:
   :show-inheritance:

---------------
AssemblyHandler
---------------

This class, utilises ``ISA`` and ``Codeline`` to parse a **single** assembly file and store its code
in chunks (lists) of ``Codeline`` objects. It offers utilities for removing and restoring arbitrary 
lines of code from the file while keeping track of the changes performed and accurately updating the
``lineno`` attributes of the stored code lines when needed.

.. autoclass:: asm.AssemblyHandler
   :members:
   :undoc-members:
   :show-inheritance: