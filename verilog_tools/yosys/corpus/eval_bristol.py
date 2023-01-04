import argparse, sys
from binascii import unhexlify
from collections import deque
from progressbar import progressbar


def main():

    parser = argparse.ArgumentParser(
        description="process a json netlist file from yosys into a bristol MPC circuit format on stdout"
    )
    parser.add_argument(
        "bristol_file",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="input filename to parse",
    )
    parser.add_argument(
        "witness",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="File to read witness from",
    )
    parser.add_argument(
        "--eval_file",
        type=argparse.FileType("w"),
        default="eval.txt",
        help="File to dump wire state",
    )
    args = parser.parse_args()

    eval_bristol(args.bristol_file, args.witness, args.eval_file)


def to_bin_str(i: int) -> str:
    assert 0 <= i < 256, "Byte out of range"
    return "{:08b}".format(i)


def eval_bristol(bristol_file, witness, eval_file):
    # fixed_input = [0, 1] + [int(i) for i in "".join(map(to_bin_str, unhexlify("DEADBEEF")))]
    fixed_input = [int(i) for i in witness.read().strip()]

    wires = {}
    output_info = {}
    lines = bristol_file.readlines()
    for line in progressbar(lines[2:]):
        line = deque(line.strip().split(" "))
        n_inputs = int(line.popleft())
        n_outputs = int(line.popleft())
        inputs = [int(line.popleft()) for _ in range(n_inputs)]
        outputs = [int(line.popleft()) for _ in range(n_outputs)]
        op = line.pop()

        if op == "INPUT":
            wire = outputs[0]
            wires[wire] = fixed_input.pop(0)
        elif op == "OUTPUT":
            wire = inputs[0]
            assert wire in wires, f"Didn't get an input for wire {wire}"
            output_info[wire] = wires[wire]
        elif op == "AND":
            out = outputs[0]
            left, right = wires[inputs[0]], wires[inputs[1]]
            if out in wires:
                print("Warning: Overwriting wire", out)
            wires[out] = left & right
        elif op == "INV":
            out = outputs[0]
            inp = inputs[0]
            if out in wires:
                print("Warning: Overwriting wire", out)
            wires[out] = 0 if wires[inp] == 1 else 1
        elif op == "XOR":
            out = outputs[0]
            left, right = wires[inputs[0]], wires[inputs[1]]
            if out in wires:
                print("Warning: Overwriting wire", out)
            wires[out] = left ^ right
        elif op == "BUF":
            out = outputs[0]
            inp = inputs[0]
            if out in wires:
                print("Warning: Overwriting wire", out)
            wires[out] = wires[inp]
        else:
            raise RuntimeError(f"UNKNOWN OPERATION: {op}")

    for k, v in output_info.items():
        print("Output", k, "::", v)

    print(wires, file=eval_file)


if __name__ == "__main__":
    main()
