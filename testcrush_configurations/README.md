# Configuration Files Format #
TOML was selected as the most user friendly format for specifying
all the key components testcrush needs to operate. Each TOML file
expects a pre-defined set of keys to be present. Hence, the user
has to only modify the corresponding values to the key.

>Important Remark: All string values are BASIC strings (`''`) and not (`""`).

>Important Remark: All values in keys that have `regex` in their name are transformed into `re.Patterns('your_regex', re.DOTALL)`.

# User Defines Section #
Since TestCrush requires the definition of auxiliary files and paths to recognize the presence of various components (e.g., the run directory of Z01X, the paths to STL source assembly files), we provide a `user_defines` section. In this section, users can define custom key-value pairs (such as paths), which can then be referenced in subsequent TOML sections using the format `%my_custom_key%`. These placeholders will be replaced with the corresponding values from the `user_defines` section during execution.

For example:
```
[user_defines]
stl_path = '../path/to/stl/dir'
root_dir = '../path/to/test/env'
```
In later sections, you can use `%stl_path%` and `%root_dir%` to dynamically substitute the paths defined above.

Note that you should NOT use keys as variables in the `user_defines`
section. For example:

✅ Do
```
[user_defines]
stl_path = '../path/to/stl/dir'
root_dir = '../path/to/test/env'
```
❌ Don't
```
[user_defines]
stl_path = '../path/to/stl/dir'
root_dir = '%stl_path%/../..'
```
As it will trigger run-time errors and incorrect substitutions.


# A0/A1xx algorithm behaviour

In this section is possible to change the algorithms behaviour:
- `compaction_policy`: defines how the algorithm decides whether to remove or restore a line of code. Currently, there are two different policies:
  - `Maximize`: the line is removed only if the new program stats improved (either TaT or Cov)
  - `Threshold`: the line is removed only if the new TaT is lower than the previous one and the fault coverage is not lower than the initial value. 

## A1xx behaviour specifics
In the A1xx algorithm, it is necessary to define the XX parameters:
- `segment_dimension`: defines the block size 
- `policy`: indicates the restoration policy:
  - `F`- forward
  - `B`- backward
  - `R`- random


# Algorithm utils

## Definition of the ISA file ##
```
[isa]
isa_file = 'path/to/your/file.isa'
```
As a suggsetion this should point to a file in the `/langs` directory.


## Assembly sources (STLs) ##
```
[assembly_sources]
sources = [
  '%stl_path%/test1.S',
  '%stl_path%/test2.S',
  ...
]
```
This is a list of paths to the assembly source files that compose your STL. It can be one or more files. Note the usage of the placeholder `'%stl_path'` which implies that this key has been earlier defined in the `user_defines` section.

## Cross-compilation instructions ##
```
[cross_compilation]
instructions = [
  'make -C %stl_path%/.. clean',
  'make -C %stl_path%/.. all'
]
```
Here we assume a `Makefile` build system to be present for the compilation of the STL sources. In this section you must specify all the steps one must take in order to cross-compile your STL and produce the firmware required for the logic and fault simulation. TestCrush assumes that the strategy is the **same** that you use when launching the logic and fault simulation tasks in your pre-existing testing environment.

## HDL sources compilation ##
```
[vcs_hdl_compilation]
instructions = [
  'make -C %root_dir% vcs/compile/gate'
]
```
Here the user must specify the instruction that one has to execute in order to compile the HDL sources for VC-Z01X. It is allowed for this list of instructions to be empty if for example a `Makefile` build system is used where it uses the compilation as a pre-requisite for logic and fault simulation.

## Logic Simulation (A) ##
```
[vcs_logic_simulation]
instructions = [
  'make -C  %root_dir% vcs/sim/gate/shell'
]
```

In this section the user must specify the command ones has to execute in order to launch a logic simulation in VCS. There must be at least 1 instructions specified by the user.

## Logic Simulation (B) ##
```
[vcs_logic_simulation_control]
timeout = 60.0
simulation_ok_regex = 'EXIT\sSUCCESS'
test_application_time_regex = 'test application time = ([0-9]+)'
test_application_time_regex_group_no = 1
```

In this section the user must specify some important parameters which will aid TestCrush to monitor and evaluate the logic simulation process. The type and usage of each parameter is the following

1. `timeout`: It acts as a wallclock for the logic simulation. It is a float number that the user must specify in **SECONDS**. If the logic simulation exceeds the timeout value then the simulation is forcibly terminated. It is suggested to be flexible with this value.
> Hint: you can use the `time` binutil to get the exact time of your logic simulation takes and use e.g., $3\times$ the `time` reported value as a timeout value here.
2. `simulation_ok_regex`: During a logic simulation a lot of things can go wrong. From an endless loop up to an out-of-bounds read or write to a memory. The simulation (in Verilog) typically ends when a terminating call is invoked from the testbench e.g., `$finish`, `$fatal` etc. To know whether the simulation ended successfully it is typically advised to have a `$display("OK MESSAGE")` right before the successful `$finish` statement. Here the user must specify a **regular expression** that captures ONLY the ok message. This is the criterion that TestCrush uses to evaluate the logic simulation as sucessful. If not specified, or specified poorly, then there will be unknown behavior.
> Hint: if no `$display()` function is used in your testbench before the correct `$finish` statement, then you can use a regexp to capture the text that the logic simulator reports when the `$finish` is reached from the **CORRECT** line number of the testbench. For instance:
`$finish called from file "my_tb", line 155.`
> Hint: Use tools like [regex101](www.regex101.com) to formulate your regexp
3. `test_application_time_regex`: Here the user must specify a regular expression with at least 1 capture groups (`()`) to match the text line from the logic simulator that reports the test application time. This can be for example the result of a `$display()` call to a custom clock counter register that your testbench implemets which captures all `posedges` of your `clk` signal.
  > Hint: If you have no such construct in your testbench to report the test application time, then you can use the default number reported by the VCS simulator. For instance the logic simulator at the end of the simulation prints out something like this: `$finish at simulation time  482140ns`. For that case the regex would be `'\$finish[^0-9]+([0-9]+)[m|u|n|p]s'`. Note the capture group `()` which holds the simulator reported nanosecond value.

4. `test_application_time_regex_group_no`: The capture group index for the `test_application_time_regex` you provided earlier. Note that this index is **not** zero-based; it is one-based.

## Fault Simulation (A) ##
```
[zoix_fault_simulation]
instructions = [
  'make -C %root_dir% vcs/fgen/saf',
  'make -C %root_dir% vcs/fsim/gate/shell'
]
```
Here, similarly as before, the user must define the instructions one has to execute to perform a fault simulation. The list must have at least 1 instruction.

## Fault Simulation (B) ##
```
[zoix_fault_simulation_control]
timeout = 360.0
allow_regexs = ['Info: Connected to started server']
```
In this section, the user must define parameters to assist TestCrush evaluate and control a fault simulation. These are:

1. `timeout`: Similar to the timeout value used for the logic simulation. A float number in **SECONDS** to be used as a wall-clock. If the fault simulation exceeds this value then it is forcibly terminated.
2. `allow_regexs`: A list of regular expressions to be used for matching in the `stderr` stream during fault simulation. The fault simulation is invoking Z01X via a `subprocess` call. To know if a simulation is successful we check whether something is written in the `stderr` stream during the `subprocess.Popen` call. If something is written there, then the fault simulation status is set to `ERROR`. However, it may be the case (as happens with the Z01X version I am working on) that something is written in the standard error which is not the result of an erroneous action. These regular expressions are used for this purpose. To allow specific messages on the `stderr` stream.
> Hint: If you are unsure on whether something is written in `stderr` during faults simulation in your test environment, then you can use a wildcard '*' (not advised however).

> 💡Q: But how am i supposed to know what exactly Z01X writes to `stderr`?

> 💡A: Good point. We plan to implement a mechanism that during `pre_run`, if text is detected in `stderr` then the user will be asked ONCE whether its "Safe". If the user types yes then its kept as message and ignored for all subsequent fault simulations.

## Fault Report ##
```
[fault_report]
###########################
# Z01X Fsim Report        #
###########################
frpt_file = '%root_dir%/run/vc-z01x/fsim_attr'
coverage_formula = 'Observational Coverage'
```
1. `frpt_file`: The canonical path in which the txt fault reports of Z01X will be stored.
2. `coverage_formula`: The **name** of the formula in the `Coverage{}` section that you want to compute.

# Attribute-Trace-based Preprocessor Configuration #
Preprocessing, is optionally available. In order to enable it you must specify the following settings:
```
[preprocessing]
###########################
# Trace required          #
###########################
processor_trace = '%sbst_dir%/trace.log'
processor_name = 'CV32E40P'
elf_file = '%sbst_dir%/sbst.elf'
zoix_to_trace = { 'PC_ID' = 'PC', 'sim_time' = 'Time'}
```
1. `enabled`: A flag to enable preprocessing (`true`/`false`)
2. `processor_trace`: The location of the txt execution trace of the STL.
3. `processor_name`: The name of the processor. MUST be one of the supported processors [TraceTransformerFactory](../src/testcrush/grammars/transformers.py#L430)
4. `elf_file`: The path to the `.elf` file of the original STL
5. `zoix_to_trace`: A mapping of Z01X fault attributes to trace column names.
