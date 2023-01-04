from abc import ABC
from typing import List

"""
Formerly contained gate representations used by the Bristol converter. Since we've switched to the Rust version we no
longer need it, but I'm not deleting it yet in case it proves useful for something. 
"""


class Gate(ABC):
    n_inputs: int = 2
    n_outputs: int = 1

    def __init__(self, input_wires: List[int], output_wires: List[int]):
        assert (
            i := len(input_wires)
        ) == self.n_inputs, f"{self.name} requires {self.n_inputs} inputs, not {i}"
        assert (
            o := len(output_wires)
        ) == self.n_outputs, f"{self.name} requires {self.n_outputs} outputs, not {o}"
        self.inputs: List[int] = [int(i) for i in input_wires]
        self.outputs: List[int] = [int(i) for i in output_wires]

    @property
    def name(self):
        return type(self).__name__

    def __str__(self):
        return " ".join(
            str(j)
            for j in [
                self.n_inputs,
                self.n_outputs,
                *self.inputs,
                *self.outputs,
                self.name,
            ]
        )


class AND(Gate):
    __slots__ = ["inputs", "outputs"]
    pass


class XOR(Gate):
    __slots__ = ["inputs", "outputs"]
    pass


class INV(Gate):
    __slots__ = ["inputs", "outputs"]
    n_inputs = 1


class INPUT(Gate):
    __slots__ = ["inputs", "outputs"]
    n_inputs = 0
    n_outputs = 1


class OUTPUT(Gate):
    __slots__ = ["inputs", "outputs"]
    n_inputs = 1
    n_outputs = 0


class BUF(Gate):
    __slots__ = ["inputs", "outputs"]
    n_inputs = 1


def mk_gate(op: str, inputs: List[int], outputs: List[int]):
    cls = {"AND": AND, "XOR": XOR, "NOT": INV, "INV": INV, "ALIAS": BUF, "BUF": BUF}[
        op.upper()
    ]
    return cls(input_wires=inputs, output_wires=outputs)


import unittest


class TestGates(unittest.TestCase):
    def test_names(self):
        self.assertEqual("AND", AND([1, 2], [3]).name)
        self.assertEqual("XOR", XOR([1, 2], [3]).name)
        self.assertEqual("INV", INV([2], [3]).name)

    def test_init(self):
        AND([1, 2], [3])
        XOR([1, 2], [3])
        INV([2], [3])

        with self.assertRaises(AssertionError):
            INV([1, 2], [3])
        with self.assertRaises(AssertionError):
            INV([2], [])
        with self.assertRaises(AssertionError):
            INV([], [])

        with self.assertRaises(AssertionError):
            AND([1, 2], [3, 4])
        with self.assertRaises(AssertionError):
            AND([2], [])
        with self.assertRaises(AssertionError):
            AND([], [])

        with self.assertRaises(AssertionError):
            XOR([2], [3])
        with self.assertRaises(AssertionError):
            XOR([2], [])
        with self.assertRaises(AssertionError):
            XOR([], [5])

    def test_format(self):
        self.assertEqual("2 1 1 2 3 AND", str(AND([1, 2], [3])))
        self.assertEqual("2 1 1 2 3 XOR", str(XOR([1, 2], [3])))
        self.assertEqual("1 1 2 3 INV", str(INV([2], [3])))
        self.assertEqual("2 1 4 5 3 AND", str(AND([4, 5], [3])))
        self.assertEqual("2 1 9 8 3 XOR", str(XOR([9, 8], [3])))
        self.assertEqual("1 1 9 7 INV", str(INV([9], [7])))


if __name__ == "__main__":
    unittest.main()
