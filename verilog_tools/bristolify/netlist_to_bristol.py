"""
READ ME FIRST

Everything in this file has been converted to Rust and no longer works with the rest of our tools.
We can safely delete it since it's preserved in the git history, but for the time being it's sticking
around as a reference in case we decide to re-implement a Python API for the Rust code.
"""

from __future__ import print_function


import json
import argparse

import sys
import gc

from typing import Dict, TextIO, List, Hashable, Tuple, Optional

from sv_circuit import Flattener
from sv_circuit import Circuit as BoolCircuit
from functools import lru_cache
from collections import deque

wire_count = -1


def reset():
    global wire_count
    wire_count = -1
    get_wire_id.cache_clear()


@lru_cache(maxsize=None)
def get_wire_id(_: Hashable) -> int:  # cursed
    """
    Returns a unique numeric ID for each wire in the BLIF file
    """
    global wire_count
    return (wire_count := wire_count + 1)


def stderr_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def error_print(statement, fatal=False):
    stderr_print(f"ERROR: {statement}")
    if fatal:
        sys.exit(0)


def format_gate(op: str, wires: List[int]) -> str:
    """
    Outputs a gate as a single line in Bristol format
    """
    return f"{len(wires) - 1} 1 {' '.join(str(w) for w in wires[::-1])} {op}"


class Circuit(BoolCircuit):
    """
    Adds additional helpers to the native Rust circuit type for converting BLIF files to Bristol
    """

    def __init__(self, name: str, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.false_symbol: Hashable = 0
        self.true_symbol: Hashable = 1
        self.inputs: List[int] = []
        self.outputs: List[int] = []
        self.pending_subcircuits: Dict[str, List[List[Tuple[int, int]]]] = {}

    def set_symbols(self, true_symbol: Hashable = 1, false_symbol: Hashable = 0):
        """
        Specify special symbols that, if seen in the circuit description, should be assumed to correspond to the 1 and
        0 boolean values. For BLIF, this is usually $true and $false.
        """
        self.false_symbol = false_symbol
        self.true_symbol = true_symbol
        self.inputs.clear()
        self.inputs.append(get_wire_id(self.false_symbol))
        self.inputs.append(get_wire_id(self.true_symbol))

    def remap_wire(self, wire_from: Hashable, wire_to: Hashable):
        """
        Create a BUF gate connecting one wire to another.
        """
        self.add_gate(
            "BUF",
            (
                get_wire_id(wire_to),
                get_wire_id(wire_from),
            ),
        )

    def __str__(self):
        """
        Render the circuit into a Bristol-Fashion string. Constructs the whole thing in memory. For better performance,
        we could take a file descriptor and stream it out instead.
        """
        stderr_print("Dumping Circuit")
        return "\n".join(
            [
                f"{self.ngate()} {self.nwire()}",
                "0",
                "0",
                *(f"0 1 {i} INPUT" for i in self.inputs),
                *(format_gate(op, wires) for (op, wires) in self.all_gates()),
                *(f"1 0 {o} OUTPUT" for o in self.outputs),
            ]
        )

    def push_inputs(self):
        """
        Takes the contents of self.inputs and pushes it to the underlying Rust circuit representation.
        """
        self.set_inputs(set(self.inputs))

    def push_outputs(self):
        """
        Takes the contents of self.outputs and pushes it to the underlying Rust circuit representation.
        """
        self.set_outputs(set(self.outputs))


def make_cell(cell):
    """Convert a JSON gate into an internal gate"""
    op = cell["type"]
    inputs = []
    outputs = []

    for k, v in cell["port_directions"].items():
        if v == "input":
            inputs.extend(cell["connections"][k])
        if v == "output":
            outputs.extend(cell["connections"][k])

    return op, (*outputs, *inputs)


def circuit_from_module(module: Dict) -> Circuit:
    """Create a circuit from a flat JSON module"""
    outputs = []
    inputs = []
    for v in module["ports"].values():
        if v["direction"] == "input":
            inputs.extend(reversed(v["bits"]))
        elif v["direction"] == "output":
            outputs.extend(reversed(v["bits"]))

    circuit = Circuit("top")
    circuit.set_symbols(true_symbol=1, false_symbol=0)

    for i in inputs:
        circuit.inputs.append(get_wire_id(i))

    circuit.push_inputs()

    for op, wires in map(make_cell, module["cells"].values()):
        circuit.add_gate(op, wires)

    for o in outputs:
        circuit.outputs.append(get_wire_id(o))

    circuit.push_outputs()

    return circuit


def circuit_from_json_file(input_file: TextIO, module_name=None) -> Circuit:
    """Unpack a JSON file into a circuit"""

    reset()
    file_contents = json.load(input_file)
    input_file.close()

    modules = file_contents["modules"]
    if module_name:
        if module_name in modules:
            module = modules[module_name]
        else:
            error_print(
                f"module {module_name} not found. Available modules in file: {list(modules.keys())}",
                fatal=True,
            )
    else:
        module = sorted(modules.values(), key=lambda b: len(b["cells"]), reverse=True)[
            0
        ]

    return circuit_from_module(module)


def _chunk_inputs(inputs: deque):
    """Splits up a BLIF input/output specification by individual wire names and individual bits on that wire"""
    while inputs:
        out = []
        start = inputs[0].split("[")[0]
        while inputs and inputs[0].startswith(start):
            out.append(inputs.popleft())
        yield out


def circuit_from_blif_file(input_file: TextIO) -> Circuit:
    """Reads a BLIF file and outputs a Circuit that can be printed as Bristol"""

    reset()
    stderr_print("Building Circuit")
    circuits: Dict[
        str, Circuit
    ] = {}  # Maps names of circuits to circuit representations

    top: Optional[str] = None  # name of top module
    current: Optional[str] = None  # name of whatever module we're currently processing
    for line in input_file:
        line = deque(line.strip().split(" "))
        cmd = line.popleft()

        # Read the model specification for a given circuit.
        if cmd == ".model":
            current = line.popleft()
            if top is None:  # Top is always the first module in the file
                top = current
            circuits[current] = Circuit(current)
            circuits[current].set_symbols(true_symbol="$true", false_symbol="$false")

        # Specify the input and output interfaces for this circuit
        if cmd == ".inputs":
            for chunk in _chunk_inputs(line):
                # Reverie expect to ingest each wire in _reverse_ order, so we have to break up the input and output
                # lines by wire name, then reverse all the bits _within_ that wire.
                for i in reversed(chunk):
                    circuits[current].inputs.append(get_wire_id(i))
            # Call the helper function to sync the input list from Python to Rust
            circuits[current].push_inputs()
        elif cmd == ".outputs":
            for chunk in _chunk_inputs(line):
                for o in reversed(chunk):
                    circuits[current].outputs.append(get_wire_id(o))
            circuits[current].push_outputs()

        # Add a gate to the current circuit
        elif cmd == ".gate":
            op = line.popleft()
            out = get_wire_id(line.pop().split("=")[-1])
            inputs = [
                get_wire_id(line.popleft().split("=")[-1]) for _ in range(len(line))
            ]
            # Op should be the gate operand as a string, the wires should be a tuple of ints with the output wire first
            circuits[current].add_gate(op, (out, *inputs))

        # Create a subcircuit descriptor on the current circuit.
        elif cmd == ".subckt":
            name = line.popleft()
            mappings: List[Tuple[int, int]] = []
            for _ in range(len(line)):
                pairing = line.popleft().split("=")
                # Mappings are tuples of ints that connect wires in the parent namespace (this circuit) to the child
                # namespace (the subcircuit). We can't use a Dict for this because keys in the parent namespace can be
                # duplicated if we have a wire that's connected to multiple inputs of the subcircuit.
                mappings.append((get_wire_id(pairing[-1]), get_wire_id(pairing[0])))
            # Unfortunately because the BLIF file provides circuits in a backwards order, we probably haven't seen that
            # subcircuit yet, so we'll have to connect it up later. We use a list because we can have multiple copies of
            # the same subcircuit on one parent.
            circuits[current].pending_subcircuits.setdefault(name, []).append(mappings)

        # Used to create buffer gates. Probably shouldn't come up with the Yosys options we use.
        elif cmd == ".names" or cmd == ".conn":
            wire_from = line.popleft()
            wire_to = line.pop()
            circuits[current].remap_wire(wire_from, wire_to)

        elif cmd == ".end":  # We're done with the current module
            current = None

    input_file.close()
    gc.collect()

    # Iterate over the pending subcircuits and add them all to the circuit. We need to split up the inputs and outputs
    # appropriately, so we had to wait until we had seen all the subcircuit models.
    for name, circuit in circuits.items():
        for sub_name, mappings in circuit.pending_subcircuits.items():
            subcircuit = circuits[sub_name]  # Grab the model for this subcircuit
            for mapping in mappings:
                in_map, out_map = ([], [])  # Make split mappings for inputs and outputs
                for own_wire, sub_wire in mapping:
                    # If this mapping goes to an input, add it to the inputs list
                    if sub_wire in subcircuit.inputs:
                        in_map.append((own_wire, sub_wire))
                    # If it goes to an output, add it to the outputs list
                    if sub_wire in subcircuit.outputs:
                        out_map.append((own_wire, sub_wire))
                    # If it doesn't go anywhere, we should probably throw an error, but I haven't tested that and don't
                    # want to break something while I'm just writing documentation.
                    # if sub_wire not in subcircuit.inputs and sub_wire not in subcircuit.outputs:
                    # raise RuntimeError(f"Wire {sub_wire} does not connect to an input or output of {sub_name}")
                # Add the subcircuit descriptor with the appropriate inputs and outputs
                circuit.add_subcircuit(sub_name, in_map, out_map)

    # Create a circuit flattener and give it the top module
    flattener = Flattener(circuits[top])

    # Add the subcircuits to the flattener. Unlike the calls to Circuit.add_subcircuit, the flattener gets the whole
    # object - not just a name and a mapping of inputs to outputs. It gets just one copy of each.
    for name, circuit in circuits.items():
        if name != top:
            flattener.add_subcircuit(circuit)

    # Flatten the circuit, and replace the Rust circuit underlying the top-level circuit with the output of the
    # flattener. Since we can't downcast in Python, we can't hide the fact that the Flattener is a Rust struct and
    # thus returns a Rust type - and without this call, that Rust type would be missing all the extra information we
    # attached to the Python type.
    circuits[top].replace_underlying(flattener.flatten())

    return circuits[top]


def collect_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "input_file",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input filename to parse",
    )
    parser.add_argument(
        "--output_file_name",
        "-o",
        type=str,
        help="File to write the Bristol Fashion circuit",
    )
    parser.add_argument(
        "--module_name",
        help="If using JSON, specify the name of module you want to be the top-level in the bristol format."
        "The default will be the biggest one in the json file.",
    )
    return parser


def main():
    parser = argparse.ArgumentParser(
        description="process a json netlist file from yosys into a bristol MPC circuit format on stdout"
    )

    args = collect_args(parser).parse_args()
    circuit_from_blif_file(args.input_file).dump_bristol(args.output_file_name)


if __name__ == "__main__":
    main()
