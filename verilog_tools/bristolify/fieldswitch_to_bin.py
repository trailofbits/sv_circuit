"""
READ ME FIRST

Everything in this file has been converted to Rust and no longer works with the rest of our tools.
We can safely delete it since it's preserved in the git history, but for the time being it's sticking
around as a reference in case we decide to re-implement a Python API for the Rust code.
"""

import argparse
import os

import sys
import gc
import random
import time

from typing import Dict, TextIO, List, Hashable, Tuple, Optional

import psutil

from sv_circuit import Flattener
from sv_circuit import Circuit as BoolCircuit
from sv_circuit import CircuitCompositor
from sv_circuit import ArithCircuitBase, ArithFlattenerBase
from functools import lru_cache
from collections import deque

wire_count = 2


def reset():
    global wire_count
    wire_count = 2
    get_wire_id.cache_clear()


@lru_cache(maxsize=None)
def get_wire_id(hashable: Hashable) -> int:  # cursed
    """
    Returns a unique numeric ID for each wire in the BLIF file
    """
    if hashable == "$true":
        return 1
    elif hashable == "$false":
        return 0
    global wire_count
    return (wire_count := wire_count + 1)


wire_count_arith = 2


def reset_arith():
    global wire_count_arith
    wire_count_arith = 2
    get_wire_id_arith.cache_clear()


@lru_cache(maxsize=None)
def get_wire_id_arith(hashable: Hashable) -> int:  # cursed
    """
    Returns a unique numeric ID for each wire in the BLIF file
    """
    if hashable == "$true":
        raise RuntimeError("Can't handle constants in arithmetic circuits yet")
        return 1
    elif hashable == "$false":
        raise RuntimeError("Can't handle constants in arithmetic circuits yet")
        return 0
    global wire_count_arith
    return (wire_count_arith := wire_count_arith + 1)


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


def _chunk_inputs(inputs: deque):
    """Splits up a BLIF input/output specification by individual wire names and individual bits on that wire"""
    while inputs:
        out = []
        start = inputs[0].split("[")[0]
        while inputs and inputs[0].startswith(start):
            out.append(inputs.popleft())
        yield out


def flatten_boolean_circuit(input_file: TextIO) -> Circuit:
    """
    Reads a BLIF file and outputs a Circuit (Rust object) that can be exported as Bristol or dumped in a Reverie-
    specific binary format.
    """

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


def flatten_arithmetic_circuit(arithmetic_file: TextIO):
    """
    Similar to flatten_boolan_circuit, reads a BLIF file and outputs a Circuit (Rust object) that can be exported,
    but only in the Reverie-specific binary format (because Bristol doesn't support arithmetic circuits).
    """

    # Reset the wire IDs (in case we re-ran the flattener without exiting Python. In the long run, those probably
    # shouldn't be globals.
    reset_arith()

    circuits: Dict[
        str, Circuit
    ] = {}  # Maps names of circuits to circuit representations
    top: Optional[str] = None  # name of top module
    current: Optional[str] = None  # name of whatever module we're currently processing
    for line in arithmetic_file:
        line = deque(line.strip().split(" "))
        cmd = line.popleft()

        # Read the model specification for a given circuit.
        if cmd == ".model":
            current = line.popleft()
            if top is None:  # Top is always the first module in the file
                top = current
            circuits[current] = Circuit(current, base=ArithCircuitBase)

        # Specify the input and output interfaces for this circuit
        if cmd == ".inputs":
            for chunk in _chunk_inputs(line):
                # Reverie expect to ingest each wire in _reverse_ order, so we have to break up the input and output
                # lines by wire name, then reverse all the bits _within_ that wire.
                for i in reversed(chunk):
                    circuits[current].inputs.append(get_wire_id_arith(i))
            # Call the helper function to sync the input list from Python to Rust
            circuits[current].push_inputs()
        elif cmd == ".outputs":
            for chunk in _chunk_inputs(line):
                for o in reversed(chunk):
                    circuits[current].outputs.append(get_wire_id_arith(o))
            circuits[current].push_outputs()

        # Add a gate to the current circuit
        elif cmd == ".gate":
            op = line.popleft()
            out = get_wire_id_arith(line.pop().split("=")[-1])
            inputs = [
                get_wire_id_arith(line.popleft().split("=")[-1])
                for _ in range(len(line))
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
                mappings.append(
                    (get_wire_id_arith(pairing[-1]), get_wire_id_arith(pairing[0]))
                )
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
    arithmetic_file.close()
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
                print("Adding subcircuit:", sub_name)
                circuit.add_subcircuit(sub_name, in_map, out_map)
    # Create a circuit flattener and give it the top module
    flattener = Flattener(circuits[top], base=ArithFlattenerBase)
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


def read_connection_circuit(connection_file, bool_top, arith_top):
    """
    Reads the connection circuit spec used to connect the boolean and arithmetic circuits

    :param connection_file: BLIF encoded file-like text buffer
    :param bool_top: name of the boolean circuit to use as the first-class boolean module (must match the boolean file)
    :param arith_top: name of the arithmetic circuit to use (must match the arithmetic file)
    :return: List of BtoA gates to create, plus the translation tables between wire IDs in the connection circuit
             namespace vs the individual circuit namespaces
    """

    BtoA = []
    arithmetic_translation_table = {}
    boolean_translation_table = {}
    for line in connection_file:
        line = deque(line.strip().split(" "))
        cmd = line.popleft()

        # Read the model specification. Only one module here, so we just print the name
        if cmd == ".model":
            print("Reading connection circuit:", line.popleft())

        # Read a "gate". Since all the modules are black boxes, everything is a gate. We decide what to do based
        # on the gate "operation", which is really just the name of the module.
        elif cmd == ".gate":
            op = line.popleft()

            # If we're dealing with one of the top-level circuits, we need to record the wire translations between
            # the current namespace and the boolean/arithmetic namespaces. This is because connection circuit
            # namespace won't exist in the composite circuit, so we have to make sure we can translate its wire IDs
            # into the correct local namespaces.
            if op in {bool_top, arith_top}:
                for _ in range(len(line)):
                    # The wire assignments are in the format `LHS=RHS` where LHS is the bool/arith circuit's local
                    # namespace, and RHS is the connection circuit namespace. Our translation tables map RHS --> LHS.
                    pairing = line.popleft().split("=")
                    if op == bool_top:
                        boolean_translation_table[
                            get_wire_id(pairing[-1])
                        ] = get_wire_id(pairing[0])
                    elif op == arith_top:
                        arithmetic_translation_table[
                            get_wire_id_arith(pairing[-1])
                        ] = get_wire_id_arith(pairing[0])

            elif op.lower() == "btoa":
                # BtoA gates are used to convert 64 1-bit boolean wires into 1 64-bit arithmetic wire.

                # The output wire for the BtoA gate should be in the arithmetic circuit's local namespace
                out = get_wire_id_arith(line.popleft().split("=")[-1])

                # The input wires for the BtoA gate will be in the boolean circuit's local namespace
                inputs = [
                    get_wire_id(line.popleft().split("=")[-1]) for _ in range(len(line))
                ]

                # Encode the gate as a tuple of the form (out, [i0, i1, i2... i63])
                BtoA.append((out, inputs))
            else:
                raise RuntimeError(
                    f"We don't know how to handle {op} gates in a connection circuit yet"
                )

        # This should only ever fire if we forgot to mark one of the modules as a black box.
        elif cmd == ".subckt":
            raise RuntimeError(
                "No subcircuits allowed in the connection circuit, sorry!"
            )

    connection_file.close()
    gc.collect()

    return BtoA, boolean_translation_table, arithmetic_translation_table


def build_composite_circuit(
    boolean_file: TextIO, arithmetic_file: TextIO, connection_file: TextIO
) -> CircuitCompositor:
    """
    Takes a boolean circuit and arithmetic circuit, plus a "connection circuit" that describes how the two
    should be connected. By convention, the composite cirucit looks something like this:

    [Bool Inputs] -> [Boolean Circuit] -> [Connection Circuit (B2A Gates)] -> [Arithmetic Circuit] -> [Arith Output]

    :param boolean_file: BLIF-encoded boolean circuit
    :param arithmetic_file: BLIF-encoded arithmetic circuit
    :param connection_file: BLIF-encoded connection spec for the boolean/arithmetic circuit
    :return: CircuitCompositor, a Rust object with a `dump_bin` method to export the circuit
    """

    # Read the BLIF file for the boolean circuit and store it as a flattened circuit in-memory
    bool_conversion_time = time.time()
    bool_circuit = flatten_boolean_circuit(boolean_file)
    bool_usage = psutil.Process(os.getpid()).memory_info()
    bool_conversion_time = time.time() - bool_conversion_time

    # Do the same for the arithmetic circuit
    arith_conversion_time = time.time()
    arith_circuit = flatten_arithmetic_circuit(arithmetic_file)
    arith_usage = psutil.Process(os.getpid()).memory_info()
    arith_conversion_time = time.time() - arith_conversion_time

    # Read the connection circuit, and get the translation tables that map boolean wire IDs to arithmetic wire IDs
    connection_circuit, bool_translations, arith_translations = read_connection_circuit(
        connection_file, "zk_stmt", "zk_stmt_arith"
    )

    # Create the circuit compositor, which is a Rust object, so it takes the Rust representations (.underlying)
    # of the boolean and arithmetic circuits
    compositor = CircuitCompositor(bool_circuit.underlying, arith_circuit.underlying)

    # Ask the compositor to connect the 64-bit boolean wire buses to the individual 64-bit-integer wire buses
    # in the arithmetic circuit
    for g in connection_circuit:
        arith_untranslated, bool_untranslated = g
        arith_translated = arith_translations[arith_untranslated]
        bool_translated = [bool_translations[w] for w in bool_untranslated]

        compositor.connect(
            # The boolean wires are given as a [Low, High) range, so we add one to the maximum translated value.
            # TODO - we should maybe check that len(range(min/max bool_translated)) == 64
            arith_translated,
            (min(bool_translated), max(bool_translated) + 1),
        )

    return compositor, (
        bool_conversion_time,
        bool_usage,
        arith_conversion_time,
        arith_usage,
    )


def collect_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "boolean_circuit",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input filename to parse",
    )
    parser.add_argument(
        "arithmetic_circuit",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input filename to parse",
    )
    parser.add_argument(
        "connection_circuit",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input filename to parse",
    )
    parser.add_argument(
        "--output_file_name",
        "-o",
        type=str,
        help="File to write the Bristol Fashion circuit",
        default="zk_stmt.bin",
    )
    return parser


def main():
    parser = argparse.ArgumentParser(
        description="Convert a set of BLIF files produced by Yosys into a composite circuit for Reverie"
    )

    args = collect_args(parser).parse_args()
    composite, stats = build_composite_circuit(
        args.boolean_circuit, args.arithmetic_circuit, args.connection_circuit
    )
    composite.dump_bin(args.output_file_name)


if __name__ == "__main__":
    main()
