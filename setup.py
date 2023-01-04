import os
from setuptools import setup, find_packages

this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="verilog_tools",
    description="Zero-Knowledge Proof of Vulnerability Tools",
    long_description_content_type="text/markdown",
    long_description=long_description,
    url="https://github.com/trailofbits/sv-tools",
    author="Trail of Bits",
    version="0.0.1",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "sv-netlist = verilog_tools.yosys.netlistify:main",
            "sv-stat = verilog_tools.yosys.yosys_stat:main",
            "sv-bristol-eval = verilog_tools.yosys.corpus.eval_bristol:main",
            "sv-blif-lint = verilog_tools.blif_lint:main",
            "sv-reverie = verilog_tools.reverie.run_reverie:main",
            "sv-lucid = verilog_tools.lucid.run_lucid:main",
        ]
    },
)
