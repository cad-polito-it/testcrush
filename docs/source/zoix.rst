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

-------------
Fault Reports
-------------
We provide two classes for managing fault reports depending on their type.

~~~~~~~~~~~~~~
TxtFaultReport
~~~~~~~~~~~~~~
This class provides a simple parsing utility based on bracket-counting to extract sections from the textual
fault report of Z01X (rpt file).

.. autoclass:: zoix.TxtFaultReport
   :members:
   :undoc-members:
   :show-inheritance:

~~~~~~~~~~~~~~
CSVFaultReport
~~~~~~~~~~~~~~
This class manages the results of the fault simulation which are expected to be in a **CSV** format. Namelly,
the fault summary and the fault list which are generated when the fcm (fault campaign manager) script contains 
the ``report -csv`` instruction. For instance, if this command is specified ``report -csv -report fsim_out`` then
after the fault simulation, in the run directory a folder named ``fsim_out_csv_files`` will be generated which will
include two .csv files. The first file is called ``DEFAULT_summary.csv`` and the second ``DEFAULT_faultlist.csv``. 
These correspond to the two constructor arguments of the ``CSVFaultReport`` object.

.. autoclass:: zoix.CSVFaultReport
   :members:
   :undoc-members:
   :show-inheritance:

-----
Fault 
-----
This class is used to represent a **prime** fault. Once again, in order to abstract as musch as possible, all
attributes of the ``Fault`` class are passed as keyword arguments. Hence, they can be arbitrarily set.
For instance, assuming that we generate a fault list based on the the CSV fault report of VC-Z01X which contains
entries of faults faults like:

.. csv-table:: 
   :header: "FID", "Test Name", "Prime", "Status", "Model", "Timing", "Cycle Injection", "Cycle End", "Class", "Location"

   1, "test1", "yes", "ON", "0", "", "", "", "PORT", "top.unit.cell.portA"
   2, "test1", 1, "ON", "0", "", "", "", "PORT", "top.unit.cell.portB"
   3, "test1", "yes", "ON", "1", "", "", "", "PORT", "top.unit.cell.portC"

The header row of this CSV snippet represents the attributes of the ``Fault`` objects, with all spaces
substituted with underscores (_) (e.g., ``"Test Name" -> "Test_Name"``) and each subsequent row contains
the corresponding values to those attributes. 

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
