import argparse
from pathlib import Path

from verilog_tools.utils.external import run_and_profile, RunData

COMPOSITOR_BIN = "sv-compositor"
STAT_BIN = "sv-bin-stat"


def collect_args(parser: argparse.ArgumentParser):
    parser.add_argument("arithmetic_circuit_in", help="BLIF file to read circuit from")
    parser.add_argument("boolean_circuit_in", help="BLIF file to read circuit from")
    parser.add_argument("connection_circuit_in", help="BLIF file to read circuit from")
    parser.add_argument("composite_circuit_out", help="Binary circuit file")
    return parser


def main():

    args = collect_args(argparse.ArgumentParser()).parse_args()

    run_compositor(
        Path(args.arithmetic_circuit_in),
        Path(args.boolean_circuit_in),
        Path(args.connection_circuit_in),
        Path(args.composite_circuit_out),
    )


def run_compositor(
    arithmetic_circuit_path: Path,
    boolean_circuit_path: Path,
    connection_circuit_path: Path,
    composite_circuit_path: Path,
) -> RunData:
    if not arithmetic_circuit_path.exists():
        raise RuntimeError("Arithmetic circuit file not found!")
    if not boolean_circuit_path.exists():
        raise RuntimeError("Boolean circuit file not found!")
    if not connection_circuit_path.exists():
        raise RuntimeError("Connection circuit file not found!")
    return run_and_profile(
        [
            COMPOSITOR_BIN,
            "-a",
            arithmetic_circuit_path,
            "-b",
            boolean_circuit_path,
            "-c",
            connection_circuit_path,
            "-o",
            composite_circuit_path,
        ]
    )


def get_composite_stats(circuit_path: Path, get_wires=False):
    prof = run_and_profile(
        [
            STAT_BIN,
            "--count",
            "wires" if get_wires else "gates",
            "--circuit",
            circuit_path,
        ],
        capture=True,
    )
    return eval(prof.stdout)


if __name__ == "__main__":
    main()
