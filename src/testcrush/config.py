#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import toml
import re
import pathlib
from typing import Any

A0_KEYS = {
    "assembly_compilation_instructions": ["cross_compilation", "instructions"],
    "vcs_compilation_instructions": ["vcs_hdl_compilation", "instructions"],
    "vcs_logic_simulation_instructions": ["vcs_logic_simulation", "instructions"],
    "vcs_logic_simulation_control": ["vcs_logic_simulation_control"],
    "zoix_fault_simulation_instructions": ["zoix_fault_simulation", "instructions"],
    "zoix_fault_simulation_control": ["zoix_fault_simulation_control"],
    "fsim_report": ["fault_report", "frpt_file"],
    "coverage_formula": ["fault_report", "coverage_formula"]
}

A0_PREPROCESSOR_KEYS = {
    "processor_name": ["preprocessing", "processor_name"],
    "processor_trace": ["preprocessing", "processor_trace"],
    "zoix_to_trace": ["preprocessing", "zoix_to_trace"],
    "elf_file": ["preprocessing", "elf_file"]
}


def replace_toml_placeholders(item: Any, defines: dict[str, str]) -> dict[str, Any]:
    """Recursively replaces any string or string within list and dicts with user defined values.

    Args:
        item (Any): A string, list or dict to act upon and replace any matching %...% pattern with defines.
        defines (dict[str, str]): A dictionary whose keys will be searched on item to be replaced with the associated
                                  values.

    Returns:
        dict[str, Any]: The parsed TOML dict where all substitutions have been performed on the user-defined keys.
    """

    if isinstance(item, str):
        for key, value in defines.items():
            placeholder = f"%{key}%"
            item = item.replace(placeholder, value)
        return item

    elif isinstance(item, list):
        return [replace_toml_placeholders(sub_item, defines) for sub_item in item]

    elif isinstance(item, dict):
        return {k: replace_toml_placeholders(v, defines) for k, v in item.items()}

    else:
        # Return the item unchanged if it's not a string, list, or dict
        return item


def replace_toml_regex(item: Any, substitute: bool = False) -> dict[str, Any]:
    """
    Recursively substitues all values corresponding to keys which include 'regex' with ``re.Patterns``.

    All generated patterns have a ``re.DOTALL`` flag set.

    Args:
        item (Any): A string, list or dict to act upon and replace any regex string with re.Pattern.
        substitute (bool, optional): Flag to allow substitution of value. Defaults to False.

    Returns:
        dict[str, Any]: The parsed TOML dict where all substitutions have been performed on the regex strings.
    """
    if isinstance(item, str) and substitute:
        return re.compile(f'{item}', re.DOTALL)

    elif isinstance(item, list):
        return [replace_toml_regex(elem, substitute) for elem in item]

    elif isinstance(item, dict):
        return {k: replace_toml_regex(v, True if "regex" in k else False) for k, v in item.items()}
    else:
        return item


def sanitize_a0_configuration(config_file: pathlib.Path) -> None:
    """Checks whether all key-value pairs have been defined in the TOML file.

    Args:
        config_file (pathlib.Path): The TOML configuration file.

    Raises:
        TomlDecodeError: if loading the file fails.
        KeyError: if a key is missing from the TOML file.
    """

    try:
        config = toml.load(config_file)
    except toml.TomlDecodeError as e:
        print(f"Error decoding TOML: {e}")

    for toml_path in A0_KEYS.values():

        section = toml_path[0]

        if section not in list(config.keys()):
            raise KeyError(f"Section {section} not in {config_file}")

        if len(toml_path) > 1:
            subkeys = toml_path[1:]

            for subkey in subkeys:

                if subkey not in list(config[section].keys()):

                    raise KeyError(f"Subsection {subkey} not in {config_file}")


def parse_a0_configuration(config_file: pathlib.Path) -> tuple[str, list, dict]:
    """
    Parses the TOML configuration file of A0 and returns the A0 constructor args.

    Args:
        config_file (pathlib.Path): The configuration file.

    Returns:
        tuple: A triplet with the ISA file (str), a list of the assembly sources (strs), and a dictionary with all the
        a0 settings.
    """

    def get_nested_value(d: dict, keys: list, default=None) -> Any:
        """Helper function to get a nested value from a dictionary, safely."""

        for key in keys:

            d = d.get(key, {})

        return d if d else default

    sanitize_a0_configuration(config_file)

    config = toml.load(config_file)

    try:
        user_defines = config["user_defines"]
    except KeyError:
        pass

    if user_defines:
        config = replace_toml_placeholders(config, user_defines)

    # Change regex keys to re.Patterns
    config = replace_toml_regex(config)

    isa = config["isa"]["isa_file"]
    asm_sources = config["assembly_sources"]["sources"]

    # Dynamically build the a0_settings dictionary using the defined key mappings
    a0_settings = {setting: get_nested_value(config, path) for setting, path in A0_KEYS.items()}

    a0_preprocessor_settings = {setting: get_nested_value(config, path)
                                for setting, path in A0_PREPROCESSOR_KEYS.items()}
    return (isa, asm_sources, a0_settings, a0_preprocessor_settings)
