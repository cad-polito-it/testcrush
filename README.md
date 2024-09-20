# TestCrush: An STL Compaction Toolkit #

Software Test Library (STL) compaction is a critical concern for the industry, as system resources—often limited and valuable—must be temporarily allocated to run test code segments while the Circuit Under Test (CUT) operates in normal mode. These non-invasive tests must be executed strictly during idle time intervals to avoid any disruption to the system's regular operation. Consequently, the tests must not only meet the required coverage percentages mandated by safety standards but also minimize memory usage and execution time within the system.

TestCrush is a framework that implements compaction algorithms for an existing STLs which are written in **assembly**. It utilizes the commercial EDA tool VC-Z01X by Synopsys to conduct logic and fault simulation. This framework is based on the implementation described in the article:

>M. Gaudesi, I. Pomeranz, M. Sonza Reorda and G. Squillero, "New Techniques to Reduce the Execution Time of Functional Test Programs," in IEEE Transactions on Computers, vol. 66, no. 7, pp. 1268-1273, 1 July 2017, doi: [10.1109/TC.2016.2643663.](https://doi.org/10.1109/TC.2016.2643663)

## Dependencies 🔗 ##

In order to use TestCrush, you must have a pre-existing logic and fault simulation flow for your design. That is, a flow which supports

1. Assembly (cross-)compilation
2. VCS HDL sources compilation
3. VCS logic simulation of the assembly sources
4. VC-Z01X fault simulation via the fault campaign compiler and fault campaign manager.

Iff such a structure exists, then TestCrush can be easily attached to the flow.

## Documentation 📚 ##

You can find the documentation of testcrush [here.](https://cad-polito-it.github.io/testcrush/)

## ! TestCrush is currently under active development phase! ##

