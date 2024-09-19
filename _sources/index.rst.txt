.. TestCrush documentation master file, created by
   sphinx-quickstart on Wed Sep 11 06:49:34 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

TestCrush documentation
=======================

.. image:: _static/testcrush.png

TestCrush is a toolkit for compaction of software test libraries 
which are written in assembly. The tool expects a configuration JSON file 
from the user and a pre-existing logic and fault simulation flow for your 
design(s).

TestCrush implements the algorithms ``A0`` and ``A1xx`` of the journal publication

   M. Gaudesi, I. Pomeranz, M. S. Reorda and G. Squillero, "New Techniques to 
   Reduce the Execution Time of Functional Test Programs," in IEEE 
   Transactions on Computers, vol. 66, no. 7, pp. 1268-1273, doi: 10.1109/TC.2016.2643663.


Version 0.5.0


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   asm
   zoix
   a0
   utils