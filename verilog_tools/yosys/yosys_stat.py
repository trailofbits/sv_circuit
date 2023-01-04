from .yosys import Session
import argparse
import os

this_directory = os.path.abspath(os.path.dirname(__file__))
library = os.path.join(this_directory, "./my_library.lib")


def main():
    parser = argparse.ArgumentParser(
        "Convert a Verilog module into a netlist and print the statistics"
    )
    parser.add_argument(
        "--top",
        type=str,
        help="Top module to convert",
    )
    parser.add_argument(
        "-I",
        "--include",
        type=str,
        action="append",
        dest="includes",
        default=[],
    )
    parser.add_argument(
        "verilog_files",
        type=str,
        nargs="+",
        help="Verilog files needed to fully synthesize top module",
    )
    args = parser.parse_args()

    stat(args)


def stat(args):
    s = Session.from_verilog(*args.verilog_files, include_dirs=args.includes)
    s.hierarchy(check=True, top=args.top)
    s.proc()
    s.memory()
    s.fsm()
    s.techmap()
    s.flatten()
    s.opt(purge=True)
    s.abc(liberty=library)
    s.opt(purge=True)
    s.read_liberty(lib=library)
    print(s.stat())


if __name__ == "__main__":
    main()
