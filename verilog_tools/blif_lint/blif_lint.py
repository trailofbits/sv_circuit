import argparse
import sys
from collections import deque
from functools import reduce
from typing import TextIO, List, Set, Optional, Dict, Tuple

from dataclasses import dataclass, field


def _chunk_inputs(inputs: deque):
    """Splits up a BLIF input/output specification by individual wire names and individual bits on that wire"""
    while inputs:
        out = []
        start = inputs[0].split("[")[0]
        while inputs and inputs[0].startswith(start):
            out.append(inputs.popleft())
        yield out


@dataclass
class Circuit:
    name: Optional[str] = field(default=None)
    inputs: Set[str] = field(default_factory=lambda: {"$true", "$false"})
    outputs: Set[str] = field(default_factory=set)
    gate_inputs: Set[str] = field(default_factory=set)
    gate_outputs: Set[str] = field(default_factory=set)
    subcircuit_outputs: Set[str] = field(default_factory=set)
    subcircuit_inputs: Set[str] = field(default_factory=set)
    _subcircuit_wires: Dict[str, Set[Tuple[str, str]]] = field(default_factory=dict)

    def check(self) -> bool:
        all_okay = True
        # Check to make sure that all the outputs of this circuit have wires driving them
        undriven_outputs = self.outputs - (
            self.gate_outputs | self.subcircuit_outputs | self.inputs
        )
        if undriven_outputs:
            all_okay = False
            print(
                "Warning:",
                self.name,
                "does not emit signals on the following outputs:\n ",
                "\n  ".join(sorted(undriven_outputs)),
            )

        undriven_gate_inputs = self.gate_inputs - (
            self.gate_outputs | self.subcircuit_outputs | self.inputs
        )
        if undriven_gate_inputs:
            all_okay = False
            print(
                "Error:",
                self.name,
                "does not drive the following wires:\n ",
                "\n  ".join(sorted(undriven_gate_inputs)),
            )

        # Check to make sure none of the input wires are also output wires (will probably break the flattener)
        inout_wires = self.inputs & self.outputs
        if inout_wires:
            all_okay = False
            print(
                "Warning:",
                self.name,
                "specifies the following wires as both inputs and outputs:\n ",
                "\n  ".join(sorted(inout_wires)),
            )

        # Check if we're not giving any subcircuits the input they ask for
        undriven_subcircuit_inputs = self.subcircuit_inputs - (
            self.gate_outputs | self.subcircuit_outputs | self.inputs
        )
        if undriven_subcircuit_inputs:
            all_okay = False
            print(
                "Warning:",
                self.name,
                "does not provide inputs to the following subcircuit wires:\n ",
                "\n  ".join(sorted(undriven_subcircuit_inputs)),
            )

        return all_okay

    def adjust_for_subcircuit_io(self, circuits: Dict):
        for name, io in self._subcircuit_wires.items():
            subc: Circuit = circuits[name]
            for (child_wire, own_wire) in io:
                if child_wire in subc.outputs:
                    self.subcircuit_outputs.add(own_wire)
                elif child_wire in subc.inputs:
                    self.subcircuit_inputs.add(own_wire)


def check_model(lines: List[deque]):
    circuit = Circuit()

    for line in lines:
        cmd = line.popleft()

        if cmd == ".model":
            circuit.name = line.popleft()
        if cmd == ".inputs":
            for chunk in _chunk_inputs(line):
                for i in reversed(chunk):
                    circuit.inputs.add(i)
        elif cmd == ".outputs":
            for chunk in _chunk_inputs(line):
                for o in reversed(chunk):
                    circuit.outputs.add(o)
        elif cmd == ".gate":
            _op = line.popleft()
            out = line.pop().split("=")[-1]
            circuit.gate_inputs.update(
                line.popleft().split("=")[-1] for _ in range(len(line))
            )
            circuit.gate_outputs.add(out)
        elif cmd == ".subckt":
            name = line.popleft()
            for _ in range(len(line)):
                pairing = tuple(line.popleft().split("="))
                # We don't know which wires of the subcircuit are inputs and which are outputs, so we'll have to figure
                # that out later
                circuit._subcircuit_wires.setdefault(name, set()).add(pairing)
        elif cmd == ".end":
            return circuit


def read_blif(input_file: TextIO):
    """
    Reads a BLIF file and outputs a Circuit (Rust object) that can be exported as Bristol or dumped in a Reverie-
    specific binary format.
    """
    circuits = {}

    model: List[deque] = []
    for line in input_file:
        line = deque(line.strip().split(" "))
        cmd = line[0]

        if line:
            model.append(line)

        # Read the model specification for a given circuit.
        if cmd == ".model":
            model.clear()
            model.append(line)
        elif cmd == ".end":  # We're done with the current module
            circuit = check_model(model)
            circuits[circuit.name] = circuit

    def return_check(circuit):
        circuit.adjust_for_subcircuit_io(circuits)
        return circuit.check()

    if reduce(
        lambda okay, circuit: okay & return_check(circuit), circuits.values(), True
    ):
        print("Okay!")


def collect_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "circuit",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input filename to lint",
    )
    return parser


def main():
    parser = argparse.ArgumentParser(
        description="Check a BLIF file for undriven outputs"
    )

    args = collect_args(parser).parse_args()
    read_blif(args.circuit)


if __name__ == "__main__":
    main()
