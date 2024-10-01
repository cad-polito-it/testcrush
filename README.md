[![Python3 Unit Tests](https://github.com/cad-polito-it/testcrush/actions/workflows/unit_tests.yaml/badge.svg)](https://github.com/cad-polito-it/testcrush/actions/workflows/unit_tests.yaml) ![Static Badge](https://img.shields.io/badge/Docs-Available-cyan)



# :clamp: TestCrush: An STL Compaction Toolkit :clamp: #

Software Test Library (STL) compaction is a critical concern for the industry, as system resources—often limited and valuable—must be temporarily allocated to run test code segments while the Circuit Under Test (CUT) operates in normal mode. These non-invasive tests must be executed strictly during idle time intervals to avoid any disruption to the system's regular operation. Consequently, the tests must not only meet the required coverage percentages mandated by safety standards but also minimize memory usage and execution time within the system.

TestCrush is a prototypical toolkit, written in 🐍 `Python3 (>=3.10)`, that implements compaction algorithms for pre-existing STLs which are written in **assembly**. It is an implementation of the compaction algorithms described in the article:

>M. Gaudesi, I. Pomeranz, M. Sonza Reorda and G. Squillero, "New Techniques to Reduce the Execution Time of Functional Test Programs," in IEEE Transactions on Computers, vol. 66, no. 7, pp. 1268-1273, 1 July 2017, doi: [10.1109/TC.2016.2643663.](https://doi.org/10.1109/TC.2016.2643663)

## Dependencies 🔗 & Architecture 📐 ##

To use TestCrush, you must have an existing logic and fault simulation flow in `VC-Z01X` for the hardware design that the STL being compacted corresponds to. TestCrush interacts with these flows through callbacks, which are specified to the framework via a [configuration file](testcrush_configurations/README.md) written in `TOML`. The architecture of TestCrush is shown in the figure below:

![TestCrush Architecture](docs/source/_static/testcrush_architecture.drawio.png)

## Documentation 📚 ##
You can find the documentation of TestCrush [here.](https://cad-polito-it.github.io/testcrush/)

## :construction: TestCrush is currently under active development phase :construction: ##

