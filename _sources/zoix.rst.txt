============
Z01X Related 
============

The ``zoix.py`` module contains utilities to perform calls to `VC-Z01X <https://www.synopsys.com/verification/simulation/vc-z01x.html>`_ 
It is based on the `subprocess <https://docs.python.org/3/library/subprocess.html>`_ package and depends heavily on user-defined parameters.

-----------
ZoixInvoker
-----------
This class is the responsible for issuing calls to VC-Z01X. It offers utilities to compile HDL sources in VCS,
logic simulate these sources, and finally, fault simulate the sources in Z01X. It assumes a pre-existing 
tested and working VC-Z01X environment for a DUT and all function arguments 
are passed as variadic args and keyword arguments. The reason for this design choice is to abstract as much as
possible from any version-specific niece that VC-Z01X might have. Hence, we offer this layer of abstraction and
leave it to the user to specify compilation and simulation isntructions to be executed in the methods of the
``ZoixInvoker`` e.g., by the TOML configuration file.


.. autoclass:: zoix.ZoixInvoker
   :members:
   :undoc-members:
   :show-inheritance:

--------------
TxtFaultReport
--------------

It provides a parsing utility based on bracket-counting to extract sections from the textual
fault report of Z01X (rpt file). Furthermore, it utilizes the supported grammars to extract and transform
sections of the fault report to manageable objects and data structures. Also, it computes coverage formulas.

.. autoclass:: zoix.TxtFaultReport
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: fault_report_path, fault_report, fault_list, status_groups, coverage

-----
Fault 
-----
This class is used to represent a **prime** fault. Once again, in order to abstract as musch as possible, all
attributes of the ``Fault`` class are passed as keyword arguments. Hence, they can be arbitrarily set.

With that said, each fault has two default, static attributes set by the constructor. These two attributes are
the ``equivalent_to`` which expects another ``Fault`` type and by default is set  to ``None`` and ``equivalent_faults`` 
which is an integer set to 1 counting the number of equivalent faults mapped to the current fault. These attributes can
be accessed and modified in an ad-hoc manner.

.. autoclass:: zoix.Fault
   :members:
   :undoc-members:
   :show-inheritance:

--------------------------
VC-Z01X Status Enumerators
--------------------------

.. autoclass:: zoix.Compilation
   :members:
   :undoc-members:
   :show-inheritance:


.. autoclass:: zoix.LogicSimulation
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: zoix.FaultSimulation
   :members:
   :undoc-members:
   :show-inheritance:
