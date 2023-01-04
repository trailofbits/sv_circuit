import argparse
import subprocess
import typing
from pathlib import Path

from verilog_tools.utils.external import run_and_profile, RunData

REVERIE_BIN = "speed-reverie"


def get_reverie_version():
    proc = subprocess.run(
        [
            REVERIE_BIN,
            "--operation",
            "version_info",
        ],
        capture_output=True,
    )
    output = {
        "reverie_version": None,
        "reverie_commit_sha": None,
        "reverie_uncommitted_changes": None,
    }
    for line in proc.stdout.split(b"\n"):
        line = line.decode("utf-8").strip()
        if line:
            tokens = line.split(": ")
            output[tokens[0]] = tokens[-1]
    return output


def collect_args(parser: argparse.ArgumentParser):
    parser.add_argument("circuit_path", help="Bristol file to read circuit from")
    parser.add_argument(
        "witness_path",
        help="Text file to read witness from. Should be encoded using ASCII 1's and 0' and start with the string `01`",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Don't delete the proof after running Reverie",
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        default="bin",
        choices=["bin", "bristol"],
        help="Intermediate program format to use",
    )

    return parser


def main():

    args = collect_args(argparse.ArgumentParser()).parse_args()

    run_reverie(
        Path(args.circuit_path),
        Path(args.witness_path),
        Path(".proof.out"),
        args.keep,
    )


def run_reverie(
    circuit_path: Path,
    witness_path: Path,
    proof_path: Path,
    keep=False,
) -> typing.Tuple[RunData, RunData]:
    if not circuit_path.exists():
        raise RuntimeError("Bristol file not found!")
    if not witness_path.exists():
        raise RuntimeError("Witness not found!")
    prof1: RunData = run_and_profile(
        [
            REVERIE_BIN,
            "--operation",
            "prove",
            "--program-path",
            circuit_path,
            "--proof-path",
            proof_path,
            "--witness-path",
            witness_path,
        ]
    )

    if not proof_path.exists():
        raise RuntimeError("Reverie did not emit a proof!")

    prof2: RunData = run_and_profile(
        [
            REVERIE_BIN,
            "--operation",
            "verify",
            "--program-path",
            circuit_path,
            "--proof-path",
            proof_path,
        ],
        capture=True,
    )

    if not keep:
        proof_path.unlink()

    return prof1, prof2


if __name__ == "__main__":
    main()
