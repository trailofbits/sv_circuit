# from pwnlib.tubes.process import process
import psutil
import subprocess


def remove_prefix(text, prefix):
    """https://stackoverflow.com/a/16892491"""
    return text[text.startswith(prefix) and len(prefix) :]


class YosysError(Exception):
    pass


class Session:
    """
    A wrapper around pwnlib.tubes.process that makes it easier to interact with Yosys via Python.

    It makes Yosys commands available as top-level python functions. For example:

    ```
    s = Session.from_verilog("processor.v", "helpers.v")
    s.read_verilog("msp430/core.v")
    s.hierarchy(check=True, top="processor_check")
    s.opt()
    s.flatten()
    s.opt(purge=True)
    print(s.stat())
    ```
    """

    _exported_functions = {
        "abc",
        "add",
        "aigmap",
        "alumacc",
        "anlogic_determine_init",
        "anlogic_eqn",
        "assertpmux",
        "async2sync",
        "attrmap",
        "attrmvcp",
        "blackbox",
        "bugpoint",
        "cd",
        "check",
        "chformal",
        "chparam",
        "chtype",
        "clean",
        "clk2fflogic",
        "connect",
        "connwrappers",
        "coolrunner2_sop",
        "copy",
        "cover",
        "cutpoint",
        "debug",
        "delete",
        "deminout",
        "design",
        "determine_init",
        "dff2dffe",
        "dff2dffs",
        "dffinit",
        "dfflibmap",
        "dffsr2dff",
        "dump",
        "echo",
        "ecp5_ffinit",
        "edgetypes",
        "equiv_add",
        "equiv_induct",
        "equiv_make",
        "equiv_mark",
        "equiv_miter",
        "equiv_opt",
        "equiv_purge",
        "equiv_remove",
        "equiv_simple",
        "equiv_status",
        "equiv_struct",
        "eval",
        "expose",
        "extract",
        "extract_counter",
        "extract_fa",
        "extract_reduce",
        "flatten",
        "flowmap",
        "fmcombine",
        "freduce",
        "fsm",
        "fsm_detect",
        "fsm_expand",
        "fsm_export",
        "fsm_extract",
        "fsm_info",
        "fsm_map",
        "fsm_opt",
        "fsm_recode",
        "greenpak4_dffinv",
        "help",
        "hierarchy",
        "hilomap",
        "history",
        "ice40_braminit",
        "ice40_dsp",
        "ice40_ffinit",
        "ice40_ffssr",
        "ice40_opt",
        "ice40_unlut",
        "insbuf",
        "iopadmap",
        "json",
        "log",
        "ls",
        "ltp",
        "lut2mux",
        "maccmap",
        "memory",
        "memory_bram",
        "memory_collect",
        "memory_dff",
        "memory_map",
        "memory_memx",
        "memory_nordff",
        "memory_share",
        "memory_unpack",
        "miter",
        "mutate",
        "muxcover",
        "muxpack",
        "nlutmap",
        "onehot",
        "opt",
        "opt_clean",
        "opt_demorgan",
        "opt_expr",
        "opt_lut",
        "opt_merge",
        "opt_muxtree",
        "opt_reduce",
        "opt_rmdff",
        "peepopt",
        "plugin",
        "pmux2shiftx",
        "pmuxtree",
        "prep",
        "proc",
        "proc_arst",
        "proc_clean",
        "proc_dff",
        "proc_dlatch",
        "proc_init",
        "proc_mux",
        "proc_rmdead",
        "qwp",
        "read",
        "read_aiger",
        "read_blif",
        "read_ilang",
        "read_json",
        "read_liberty",
        "read_verilog",
        "rename",
        "rmports",
        "sat",
        "scatter",
        "scc",
        "script",
        "select",
        "setattr",
        "setparam",
        "setundef",
        "sf2_iobs",
        "share",
        "shell",
        "show",
        "shregmap",
        "sim",
        "simplemap",
        "splice",
        "splitnets",
        "stat",
        "submod",
        "supercover",
        "synth",
        "synth_achronix",
        "synth_anlogic",
        "synth_coolrunner2",
        "synth_easic",
        "synth_ecp5",
        "synth_gowin",
        "synth_greenpak4",
        "synth_ice40",
        "synth_intel",
        "synth_sf2",
        "synth_xilinx",
        "tcl",
        "techmap",
        "tee",
        "test_abcloop",
        "test_autotb",
        "test_cell",
        "torder",
        "trace",
        "tribuf",
        "uniquify",
        "verific",
        "verilog_defaults",
        "verilog_defines",
        "wbflip",
        "wreduce",
        "write_aiger",
        "write_blif",
        "write_btor",
        "write_edif",
        "write_file",
        "write_firrtl",
        "write_ilang",
        "write_intersynth",
        "write_json",
        "write_simplec",
        "write_smt2",
        "write_smv",
        "write_spice",
        "write_table",
        "write_verilog",
        "zinit",
    }

    @classmethod
    def from_verilog(cls, *files, yosys_path="yosys", **kwargs):
        inst = cls(yosys_path=yosys_path)
        inst.read_verilog(*files, **kwargs)
        return inst

    @staticmethod
    def _filter_kwargs(**kwargs) -> str:
        """Converts kwargs into command line strings. For example:

        {"module": "circuit"} becomes `-module circuit`
        {"color": [100, "circuit]} becomes `-color 100 circuit`
        {"top": True} becomes `-top`
        """
        tokens = []
        for k in kwargs:
            if kwargs[k] is None:
                pass
            elif isinstance(kwargs[k], bool) and kwargs[k]:
                tokens.append(f"-{k.replace('_', '-')}")
            elif isinstance(kwargs[k], list):
                tokens.append(f"-{k} {' '.join(str(i) for i in kwargs[k])}")
            else:
                tokens.append(f"-{k} {str(kwargs[k])}")

        return " ".join(tokens)

    def __init__(self, yosys_path="yosys"):
        self._path = yosys_path
        self.p = None
        self.running = False
        self.restart()
        self.history = []

    def restart(self):
        """Initialize the Yosys process"""
        if self.running:
            self.exit()
        self.p = subprocess.Popen(self._path)
        self.p.recvuntil(b"yosys> ")
        self.running = True

    def _run_raw_cmd(self, cmd: str):
        """Passed cmd to yosys. Confirms that Yosys is running, but other than that has no
        error handling. Cleans up the output by UTF-8 formatting and stripping it."""
        if not self.running:
            raise RuntimeError(
                "This session has exited! Use .restart to reinitialize it."
            )
        self.history.append(cmd)
        self.p.sendline(cmd)
        return (
            remove_prefix(self.p.recvuntil(b"yosys> ", drop=True).decode("utf-8"), cmd)
            .strip()
            .lstrip()
        )

    def _run_cmd(self, cmd, *args, **kwargs):
        """Formats the provided command with *args and **kwargs, and passes the result to
        _run_raw_cmd. Handles EOFError in case of crashed processes. Raises YosysError if
        the command did not complete successfully."""
        cmd_str = (f"{cmd} {self._filter_kwargs(**kwargs)} " + " ".join(args)).strip()
        result = ""
        try:
            result = self._run_raw_cmd(cmd_str)
        except EOFError:
            self.running = False
            print(result)
            raise YosysError(f"This command caused Yosys to exit: {cmd_str}")
        if "ERROR:" in result:
            raise YosysError(
                "\n========\n" + result.split("ERROR: ")[-1] + "\n========"
            )
        return result

    def __getattr__(self, item):
        """Allows the calling of Yosys functions listed in self._exported_functions"""
        if item not in self._exported_functions:
            raise AttributeError(f"Can't find a Yosys command called {item}")

        def f(*args, **kwargs):
            return self._run_cmd(item, *args, **kwargs)

        return f

    def read_verilog(self, *args, macros={}, include_dirs=[], **kwargs):
        return self._run_cmd(
            "read_verilog",
            *[f"-I{dir_}" for dir_ in include_dirs],
            *(tuple(f"-D{k}={v}" for k, v in macros.items())),
            *(str(a) for a in args),
            **kwargs,
        )

    def exit(self):
        try:
            self._run_raw_cmd("exit")
        except EOFError:
            pass
        self.running = False

    def dump_history(self):
        return ";\n".join(self.history)

    def memory_usage(self):
        if not self.running:
            return None
        proc = psutil.Process(self.p.proc.pid)
        return proc.memory_info()
