import unittest
from gates import AND, XOR, INV


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
