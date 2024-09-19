===========
zoix module
===========

The ``zoix.py`` module contains utilities to perform calls to `VC-Z01X <https://www.synopsys.com/verification/simulation/vc-z01x.html>`_ 
It is based on the `subprocess <https://docs.python.org/3/library/subprocess.html>`_ package and depends heavily on user-defined parameters.

-----------
ZoixInvoker
-----------
This class is the responsible for issuing calls to VC-Z01X. It offers utilities to compile HDL sources in VCS,
logic simulate these sources, generate fault campaign manager sripts and finally, fault simulate the sources
in Z01X. It assumes a pre-existing a tested and working VC-Z01X environment for a DUT and all function arguments
are passed as variadic args and keyword arguments. The reason for this design choice is to abstract as much as
possible from any version-specific niece that VC-Z01X might have. Hence, we offer this layer of abstraction and
leave it to the user to specify compilation and simulation isntructions to be executed in the methods of the
``ZoixInvoker`` e.g., by a .json configuration file.


.. autoclass:: zoix.ZoixInvoker
   :members:
   :undoc-members:
   :show-inheritance:


--------------
CSVFaultReport
--------------
This class manages the results of the fault simulation which are expected to be in a **CSV** format. Namelly,
the fault summary and the fault list which are generated when the fcm (fault campaign manager) script contains 
the ``report -csv`` instruction. This is a **hard** requirement for the whole TestCrush framework to work. The
reason for not relying on the textual fault reports is once again the nieces that are introduced in different
VC-Z01X versions. The ``.txt`` fault summary and report are sometimes poorly indented, and in general require
regexp parsing. Hence, the CSVs. Nothing can go wrong with an ol'reliable format like this.

.. autoclass:: zoix.CSVFaultReport
   :members:
   :undoc-members:
   :show-inheritance:

-----
Fault 
-----
This class is used to represent a fault. However, once again in order to make it as general as possible, all
attributes of the ``Fault`` class are passed as keyword arguments. Hence, they can be arbitrarily selected.
For instance, the CSV fault report of VC-Z01X contains the faults like this:

>>>
"FID","Test Name","Prime","Status","Model","Timing","Cycle Injection","Cycle End","Class","Location"
1,"test1","yes","ON","0","","","","PORT","tb_top.wrapper_i.top_i.core_i.ex_stage_i.alu_i.U10.Z"
2,"test1",1,"ON","0","","","","PORT","tb_top.wrapper_i.top_i.core_i.ex_stage_i.alu_i.U10.A"
3,"test1","yes","ON","1","","","","PORT","tb_top.wrapper_i.top_i.core_i.ex_stage_i.alu_i.U10.Z"

The header row of this CSV snippet represents the attributes of the ``Fault`` objects, with all spaces
substituted with underscores (_) (e.g., ``"Test Name" -> "Test_Name"``) and each subsequent row contains
the corresponding values to those attributes. Its used by the ``CSVFaultReport`` for coverage computation
and fault list parsing.

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
