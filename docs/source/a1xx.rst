
==============
A1xx Algorithm
==============

Implementation of the `A1xx compaction algorithm <https://doi.org/10.1109/TC.2016.2643663>`_ . The only difference 
with respect to the original A1xx algorithm is that in order to validate a removal of a block of instructions from the STL, the 
evaluation happens on whether the new test application time is less or equal than the old test application time **AND**
whether the new test coverage is **greater or equal** than the old test application time. However, with the provided
utilities provided with the toolkit this can be extended or modified to the user's needs. All it takes is a few LoC
in the evaluation method of each iteration within the A1xx class. 

A1xx
--

.. autoclass:: a1xx.A1xx
   :members:
   :undoc-members:
   :show-inheritance:

