
=============
Preprocessing
=============

-------------
It is possible to perform preprocessing in the set of assembly candidates to reduce the runtime of the A0 algorithm. The runtime of 
the algorithm solely depends on the total number of candidates to be considered in each iteration. It is a brute-force approach to 
the compaction problem. So the idea is the following. What 
if, after we execute the `pre_run()` of the A0 algorithm to obtain the initial STL statistics, we are able to assess somehow
the impact each Candidate has in terms of faults being detected?

In order to obtain such information a couple of things are required. First, we need a fault report comming from Z01X with includes
custom **fault attributes**. Secondly, we need a trace comming directly from the DUT after the execution of the original STL. The idea
is to guide algorithm by leveraging useful state information stemming from the fault detection time of each fault. Assuming that the DUT is
a pipelined processor, then this information must include (i) the simulation time and (ii) the program counter value. Then, by examining the
contents of the trace, it is possible to map these program counter values and timestamps to instructions in the trace, and identify "hot-zones"
of the STL. That is, codeline regions that contribute to the detection of the faults. 

Fault Attributes
^^^^^^^^^^^^^^^^
After a Z01X fault simulation, it is possible to enable with ``report`` command the inclusion of the fault attributes by specifying the flag ``-showallattributes``.
VC Z01X provides the ability to define custom fault attributes using key, value pairs. The fault coverage is reported in the coverage report for each key, value pair.
To add such attributes to each fault one has to modify the ``strobe.sv`` file accordingly. Here is an example of attaching the simulation time and the program counter
to a fault by modifying the strobe file.

.. code-block:: systemverilog
   
   cmp = $fs_compare(`TOPLEVEL); // Check for differences between GM and FM
   if (1 == cmp) begin
      $fs_drop_status("ON", `TOPLEVEL);
      $fs_add_attribute(1, "PC", "%h", {`TOPLEVEL.pc_id[31:1], 1'b0}); // Attach program counter
      $fs_add_attribute(1, "sim_time", "%t", $time); // Attach simulation time
   end else if (2 == cmp) begin
      $fs_drop_status("PN", `TOPLEVEL);
      $fs_add_attribute(1, "PC", "%h", {`TOPLEVEL.pc_id[31:1], 1'b0}); // Attach program counter
      $fs_add_attribute(1, "sim_time", "%t", $time); // Attach simulation time
   end

By utilizing the ``$fs_add_attribute()`` directive we can easily add the required attributes to
each detected fault. When the final fault report is generated with the ``-showallatributes`` flag,
then the attributes are attached to every prime fault like this:

   ::
      
   <  1> ON 1 {PORT "path.to.fault.site"}(* "testName"->PC="00000004"; "testName"->sim_time="   10ns"; *)

Execution Trace
^^^^^^^^^^^^^^^
The execution trace is required in order to search for the hotzones with information stemming from the attributes reported in the fault reports. 
By attaching adequate information on each fault, and of course, **relevant and acurate(!) to the one present in the trace** we can search within
the STL execution trace for instances. For instance, we can search for ``<PC, Time>`` attribute pairs stemming from the fault report to pinpoint
spatially and temporally the sequence of codelines that were executed and led to the fault detectiong. The PC values and times reported in the 
attributes of the faults must comming from the exact same signals employed by the trace. Otherwise we may have off-by-one errors in our search 
in the trace when trying to associate simulation times and program counter values for example. The trace, during processing, is written into a database, 
which can be queried for retrieving rows with information comming from the fault attributes

Preprocessor
------------

.. autoclass:: a0.Preprocessor
   :members:
   :undoc-members:
   :show-inheritance: