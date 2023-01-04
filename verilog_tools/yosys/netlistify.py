from .yosys import Session
import argparse
import os

this_directory = os.path.abspath(os.path.dirname(__file__))
library = os.path.join(this_directory, "./my_library.lib")


def collect_args(parser: argparse.ArgumentParser):
    parser.add_argument("out_fname")
    parser.add_argument(
        "--top",
        type=str,
        help="Top module to convert",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Create a JSON file instead of BLIF",
    )
    parser.add_argument(
        "--flatten",
        action="store_true",
        help="Flatten the BLIF file before emitting",
    )
    parser.add_argument(
        "--arithmetic",
        action="store_true",
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
    return parser


def main():
    args = collect_args(
        argparse.ArgumentParser(
            "Convert a Verilog module into a netlist and print the statistics"
        )
    ).parse_args()

    if args.arithmetic:
        make_arithmetic_netlist(
            args.verilog_files,
            args.out_fname,
            top=None,
            include_dirs=args.includes,
        )
    else:
        make_netlist(
            args.verilog_files,
            args.out_fname,
            top=args.top,
            json=args.json,
            include_dirs=args.includes,
            flatten=args.flatten,
        )


def make_netlist(
    verilog_files,
    out_fname,
    top=None,
    json=False,
    macros=None,
    include_dirs=[],
    flatten=False,
):
    """
    Converts a series of Verilog files into a BlIF netlist

    :param verilog_files: List of verilog files to include in synthesis
    :param out_fname: Location to write BLIF file to
    :param top: Name of top circuit to use (if needed)
    :param json: Emit JSON (instead of BLIF)
    :param macros: Verilog macros to set during synthesis
    :param include_dirs: Folder to find Verilog files in
    :param flatten: Use Yosys' flattening pass (slow and memory-inefficient)
    :return: memory usage information
    """

    macros = {} if macros is None else macros
    macros.update({"NO_DISASM": 1})
    s = Session.from_verilog(*verilog_files, macros=macros, include_dirs=include_dirs)
    if top:
        s.hierarchy(check=True, top=top)
    else:
        s.hierarchy(check=True, auto_top=True)
    s.proc()
    s.memory()
    s.fsm()
    s.techmap()
    s.opt(purge=True)
    s.abc(liberty=library)
    s.rmports()
    s.opt()  # (purge=True)
    if flatten:
        s.flatten()
    s.clean()  # (purge=True)
    s.read_liberty(lib=library)
    if json:
        s.write_json(out_fname)
    else:
        s.write_blif(out_fname, gates=True, impltf=True, buf="BUF IN OUT")

    usage = s.memory_usage()
    s.exit()

    return usage


def make_arithmetic_netlist(
    verilog_files,
    out_fname,
    top=None,
    macros=None,
    include_dirs=[],
    blackbox=frozenset(),
):
    """
    Very similar to make_netlist, but with a few of the optimizations skipped, and the option to provide a set of
    _blackbox_ modules that Yosys should not attempt to synthesize

    :param blackbox: iterable of module names to mark as black boxes
    :return: memory usage information
    """

    macros = {} if macros is None else macros
    macros.update({"NO_DISASM": 1})
    s = Session.from_verilog(*verilog_files, macros=macros, include_dirs=include_dirs)
    for b in blackbox:
        s.blackbox(b)
    if top:
        s.hierarchy(top=top)
    else:
        s.hierarchy(auto_top=True)
    s.opt(purge=True)
    s.clean(purge=True)
    s.write_blif(out_fname, gates=True, impltf=True, blackbox=True, buf="BUF IN OUT")

    usage = s.memory_usage()
    s.exit()

    return usage


if __name__ == "__main__":
    main()
