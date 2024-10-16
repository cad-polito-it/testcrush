.. TestCrush documentation master file, created by
   sphinx-quickstart on Wed Sep 11 06:49:34 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

TestCrush documentation
=======================

.. image:: _static/testcrush.png

Welcome to the documentation of TestCrush.
TestCrush is a toolkit designed to compact software test libraries written in assembly. 
It relies heavily on the (VC-)Z01X logic and fault simulator. 
The tool requires a pre-existing testing environment for evaluating the STL compaction process.


TestCrush implements the algorithms ``A0`` and ``A1xx`` of:

   M. Gaudesi, I. Pomeranz, M. S. Reorda and G. Squillero, "New Techniques to 
   Reduce the Execution Time of Functional Test Programs," in IEEE 
   Transactions on Computers, vol. 66, no. 7, pp. 1268-1273, doi: 10.1109/TC.2016.2643663.


Version 0.5.0


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   asm
   zoix
   grammar
   a0
   utils
   config