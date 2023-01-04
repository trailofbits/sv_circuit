import argparse
from pathlib import Path

from verilog_tools.utils.external import run_and_profile, RunData

LUCID_BIN = "lucid"


def collect_args(parser: argparse.ArgumentParser):
    parser.add_argument("circuit_in", help="Binary file to read circuit from")
    parser.add_argument("circuit_out", help="Binary circuit file")
    return parser


def main():

    args = collect_args(argparse.ArgumentParser()).parse_args()

    run_lucid(
        Path(args.circuit_in),
        Path(args.circuit_out),
    )


def run_lucid(
    circuit_path: Path,
    output_path: Path,
) -> RunData:
    if not circuit_path.exists():
        raise RuntimeError("Input file not found!")
    return run_and_profile(
        [
            LUCID_BIN,
            "--in",
            circuit_path,
            "--out",
            output_path,
        ]
    )


if __name__ == "__main__":
    main()
