# sv-tools

## tools
- `sv-netlist` -- Create a Netlist in BLIF or JSON format from a Verilog file(s)
- `sv-bristol` -- Convert a Netlist in BLIF or JSON format into a Bristol file
- `sv-compositor` -- Convert BLIF netlists for a Boolean, Arithmetic, and combination circuit into 
                     Reverie's circuit format
- `sv-stat` -- Temporarily convert a Verilog file(s) into a netlist and print the number of gates
- `sv-emulate` -- Run the MSP430 Emulator to produce a trace
- `sv-witness` -- Convert the program and memory traces into the ZK witness format that Reverie ingests
- `sv-bristol-eval` -- Evaluate a Bristol circuit (in Python) against a ZK witness.
- `sv-reverie` -- Run Reverie's prover and verifier on a Bristol file and a ZK witness
- `sv-lucid` -- Run the `lucid` circuit minimization tool to reduce Reverie's RAM usage
- `sv-verify` -- Run the entire pipeline (from tracing to synthesis to proving) from the top
- `sv-measure` -- Run `sv-verify` and record performance information in a spreadsheet
