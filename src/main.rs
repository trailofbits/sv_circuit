use itertools::Itertools;
use std::collections::{HashMap, VecDeque};
use std::convert::TryInto;
use std::fs::{read_to_string, File};
use std::io::{prelude::*, BufReader, BufWriter};
use std::ops::Range;
use std::path::Path;

use clap::{App, Arg};
use mcircuit::parsers::blif::{parse_split, BlifParser};
use mcircuit::parsers::WireHasher;
use mcircuit::{CombineOperation, Operation, Parse};

use std::io;
use std::mem::size_of;
use sv_circuit::{CircuitCompositor, GenericCircuit};

const WITNESS_LEN: usize = 656;

// FIXME(jl): this should be modularized.
// FIXME(jl): use anyhow! for binary crate.
fn parse_witness(path: &str) -> Vec<[bool; WITNESS_LEN]> {
    read_to_string(path)
        .expect("failed to open witness")
        .trim()
        .split('\n')
        .map(|step| {
            step.chars()
                .map(|c| match c {
                    '0' => false,
                    '1' => true,
                    _ => panic!("bad bit {:?} in witness!", c),
                })
                .collect::<Vec<bool>>()
                .try_into()
                .expect("invalid trace step length!")
        })
        .collect()
}

fn emit_ir0(
    tiny86: &GenericCircuit<bool>,
    base_fname: &str,
    witness: &[[bool; WITNESS_LEN]],
) -> Result<(), io::Error> {
    //
    // write witness.
    //
    let witness_fname = format!("{base_fname}.private_input");
    let mut witness_writer =
        BufWriter::new(File::create(witness_fname).expect("Failed to open witness file"));
    writeln!(witness_writer, "version 2.0.0-beta;")?;
    writeln!(witness_writer, "{};", "private_input")?;
    writeln!(witness_writer, "@type field 2;")?;
    writeln!(witness_writer, "@begin")?;
    for (i, step) in witness.iter().enumerate() {
        writeln!(witness_writer, "// step {}", i)?;
        for wit_value in step {
            writeln!(witness_writer, "< {} > ;", *wit_value as u32)?;
        }
    }
    writeln!(witness_writer, "@end")?;

    //
    // write instance.
    //
    let instance_fname = format!("{base_fname}.public_input");
    let mut instance_writer =
        BufWriter::new(File::create(instance_fname).expect("Failed to open instance file"));
    writeln!(instance_writer, "version 2.0.0-beta;")?;
    writeln!(instance_writer, "{};", "public_input")?;
    writeln!(instance_writer, "@type field 2;")?;
    writeln!(instance_writer, "@begin")?;
    writeln!(instance_writer, "@end")?;

    //
    // write circuit.
    //
    let circuit_fname = format!("{base_fname}.circuit");
    let mut circuit_writer =
        BufWriter::new(File::create(circuit_fname).expect("Failed to open instance file"));
    writeln!(circuit_writer, "version 2.0.0-beta;")?;
    writeln!(circuit_writer, "circuit;")?;
    writeln!(circuit_writer, "@type field 2;")?;
    writeln!(circuit_writer, "@begin")?;
    writeln!(circuit_writer, "")?;

    // emit circuit @function.
    // FIXME(jl): use `tiny86.name` &c fields here -- see `GenericCircuit`.
    writeln!(
        circuit_writer,
        "@function(tiny86, @out: 0:1, @in: 0:656, 0:656)"
    )?;
    // NOTE(lo): wire numbering in function bodies starts with the output and proceeds sequentially through the inputs
    // e.g. for the function signature above, which corresponds to tiny86(step1, step2)
    // $0 is the output wire, i.e., the value written to ok in check.v
    // $1 ... $656 are the step1 input wires
    // $657 ... $1312 are the step2 input wires

    // FIXME(lo): we need a counter to increment through the input wire indices for the Operation::Input case below, i.e.,
    // let mut input_wire_idx: usize = 0;
    // but tiny86.topo_iter() already comes with a numbering that may conflict with these indices...
    // We also don't appear to hit the Operation::Input case.

    // FIXME(jl): indent the body of the function.
    for gate in tiny86.topo_iter() {
        match gate {
            Operation::Input(_) => panic!("Input in tiny86 circuit body!"),
            Operation::Random(_) => panic!("Random unsupported!"),
            Operation::Add(o, l, r) => {
                writeln!(circuit_writer, "${} <- @add(${}, ${});", o, l, r)
            }
            Operation::AddConst(o, i, c) => {
                writeln!(
                    circuit_writer,
                    "${} <- @addc(${}, < {} >);",
                    o, i, *c as u32
                )
            }
            Operation::Sub(o, l, r) => {
                writeln!(circuit_writer, "${} <- @add(${}, ${});", o, l, r)
            }
            Operation::SubConst(o, i, c) => {
                writeln!(
                    circuit_writer,
                    "${} <- @addc(${}, < {} >);",
                    o, i, *c as u32
                )
            }
            Operation::Mul(o, l, r) => {
                writeln!(circuit_writer, "${} <- @mul(${}, ${});", o, l, r)
            }
            Operation::MulConst(o, i, c) => {
                writeln!(
                    circuit_writer,
                    "${} <- @mulc(${}, < {} >);",
                    o, i, *c as u32
                )
            }
            Operation::AssertZero(_) => panic!("Unexpected assertion in tiny86 circuit!"),
            Operation::Const(w, c) => {
                writeln!(circuit_writer, "${} <- < {} >;", w, *c as u32)
            }
        }?;
    }
    // HACK(jl): this exporting function should be independent of our tiny86 geometry;
    // here we're just lucky the number of outputs slots nicely into the area reserved for Bristol
    // True/False constants.
    assert!(tiny86.outputs.len() == 1);
    for output in tiny86.outputs.iter().sorted() {
        writeln!(circuit_writer, "$0 <- ${};", output)?;
    }

    // FIXME(lo): ok bit needs to be negated and assigned to output wire $0
    // writeln!(circuit_writer, ${} <- ${}, ok_bit_idx + 1, ok_bit_idx)?;
    // writeln!(circuit_writer, "$0 <- ${}", ok_bit_idx + 1)?;
    writeln!(circuit_writer, "@end")?;
    writeln!(circuit_writer, "\n")?;

    // FIXME(jl): note about inputs, outputs, @functions, and flattening.
    // because our wires are identified just by a unique integer,
    // flattening reserves space for:
    // - 2 wires, true and false (used for Bristol -- don't hurt us but also don't need).
    // - all inputs -- so, here the tiny86 circuit doesn't start until 2 + 656 I think.
    // - all outputs -- so, we can't use those wires for other assignments!
    //
    // I think this is missing:
    // - we have to generate $stepsize number of wires for each private input bit.
    // - plus a wire for the `ok` bit.
    // - plus a wire to invert it -- maybe, if we do really want an `@assert_one`.
    // there's going to be some funky managing to begin counting anew outside the function body.
    //
    // So we can either hack around it,
    // or maybe enable a flattening "mode" where it doesn't
    // do any reserving of bits -- then if we have a way of knowing where the flattener left off counting,
    // so just the number of wires the tiny86 body uses (currently ~46k),
    // then we can pick up counting here as we please.

    // HACK(jl): number sufficiently large enough I know the tiny86 circuit won't conflict.
    let mut wire_counter: usize = 100000;

    // emit circuit data.
    // FIXME(jl): ideally this can be caught much earlier.
    // NOTE(jl): need at least 2 traces to compare.
    assert!(witness.len() >= 2);

    let mut steps: VecDeque<Range<usize>> = VecDeque::with_capacity(2);

    for (step_count, step) in witness.iter().enumerate() {
        // fetch the private input.
        writeln!(circuit_writer, "// step {}", step_count)?;
        // NOTE(jl): this end range is asserted as correct at the exit of this loop.
        writeln!(
            circuit_writer,
            "@new(${} ... ${});",
            wire_counter,
            wire_counter + 655
        )?;
        let start = wire_counter;
        for _ in step {
            writeln!(circuit_writer, "${} <- @private();", wire_counter)?;
            wire_counter += 1;
        }
        let end = wire_counter;
        assert!(end == start + 656);
        let step_range = Range { start, end };
        steps.push_front(step_range);

        if step_count > 0 {
            // FIXME(jl): again better function metadata maintenance.
            writeln!(
                circuit_writer,
                "${} <- @call(tiny86, ${} ... ${}, ${} ... ${});",
                wire_counter,
                // previous step wire range.
                steps.back().unwrap().clone().min().unwrap(), // FIXME(jl): bleh
                steps.back().unwrap().clone().max().unwrap(),
                // current step wire range.
                steps.front().unwrap().clone().min().unwrap(),
                steps.front().unwrap().clone().max().unwrap(),
            )?;
            writeln!(circuit_writer, "@assert_zero(${});", wire_counter)?;
            steps.pop_back();
            wire_counter += 1;
        }
    }
    writeln!(circuit_writer, "@end")?;

    Ok(())
}

/// Rust version of circuit compositor
fn main() {
    let matches = command!()
        .arg(arg!(-a --arithmetic_circuit <FILE> "BLIF file"))
        .arg(arg!(-b --boolean_circuit <FILE> "BLIF file"))
        .arg(arg!(-c --connection_circuit <FILE> "Connection circuit file"))
        .arg(arg!(-w --witness <FILE> "Witness trace"))
        .arg(arg!(-o --output_file <FILE> "Compiled circuit").required(true))
        .get_matches();

    let out_fname = matches.get_one::<String>("output_file").unwrap();
    let base_fname = Path::new(out_fname)
        .file_stem()
        .and_then(|s| s.to_str())
        .expect("Failed to parse base_fname from output path");

    let maybe_arith = matches.get_one::<String>("arithmetic_circuit");
    let maybe_bool = matches.get_one::<String>("boolean_circuit");
    let maybe_conn = matches.get_one::<String>("connection_circuit");
    let maybe_witness = matches.get_one::<String>("witness");

    // compilation target determined by output file extension.
    let export_bristol = out_fname.ends_with(".bristol");
    let export_ir0 = out_fname.ends_with(".circuit");
    let export_ir1 = out_fname.ends_with(".ir1");

    match (maybe_arith, maybe_bool, maybe_conn) {
        (Some(path), None, None) => {
            let reader =
                BufReader::new(File::open(path).expect("Failed to open arithmetic circuit file"));
            let (flat, _, _) = sv_circuit::flatten(BlifParser::<u64>::new(reader));
            let writer =
                BufWriter::new(File::create(out_fname).expect("Failed to open output file"));
            bincode::serialize_into(writer, &flat).expect("Failed to write circuit");
        }
        (None, Some(path), None) => {
            let reader =
                BufReader::new(File::open(path).expect("Failed to open boolean circuit file"));
            let (flat, _, _) = sv_circuit::flatten(BlifParser::<bool>::new(reader));

            let mut writer =
                BufWriter::new(File::create(out_fname).expect("Failed to open output file"));

            let witness_path = maybe_witness.expect("no witness for Bristol circuit!");

            let w = parse_witness(witness_path);

            match (export_bristol, export_ir0, export_ir1) {
                // Bristol
                (true, false, false) => todo!(),
                // IR0
                (false, true, false) => emit_ir0(&flat, base_fname, &w),
                // IR1
                (false, false, true) => todo!(),
                _ => todo!(),
            }
            .expect("Target format compilation error.");
        }
        (Some(arith_path), Some(bool_path), Some(conn_path)) => {
            let bool_reader =
                BufReader::new(File::open(bool_path).expect("Failed to open boolean circuit file"));
            let (flat_bool, top_bool, hasher_bool) =
                sv_circuit::flatten(BlifParser::<bool>::new(bool_reader));

            let arith_reader = BufReader::new(
                File::open(arith_path).expect("Failed to open arithmetic circuit file"),
            );
            let (flat_arith, top_arith, hasher_arith) =
                sv_circuit::flatten(BlifParser::<u64>::new(arith_reader));

            let mut compositor = CircuitCompositor::new(flat_bool, flat_arith);

            let conn_reader = BufReader::new(
                File::open(conn_path).expect("Failed to open connection circuit file"),
            );
            let (b2a, bool_translations, arith_translations) = read_connection_circuit(
                conn_reader,
                (top_bool, top_arith),
                (hasher_bool, hasher_arith),
            );

            for (arith_untrans, mut bool_untrans) in b2a {
                let arith_trans = arith_translations
                    .get(&arith_untrans)
                    .expect("Arithmetic wire left untranslated");
                let bool_trans: Vec<usize> = bool_untrans
                    .drain(..)
                    .map(|u| {
                        bool_translations
                            .get(&u)
                            .expect("Boolean wire left untranslated")
                    })
                    .copied()
                    .collect();

                compositor.connect(
                    *arith_trans,
                    *bool_trans
                        .iter()
                        .min()
                        .expect("Boolean translation table was empty"),
                );
            }

            let writer =
                BufWriter::new(File::create(out_fname).expect("Failed to open output file"));

            let (bool_gate_count, bool_wire_count, b2a_count, arith_gate_count, arith_wire_count) =
                compositor.gate_stats();
            let bool_size_est = bool_gate_count * size_of::<CombineOperation>()
                + bool_wire_count * size_of::<bool>();
            let arith_size_est = arith_gate_count * size_of::<CombineOperation>()
                + arith_wire_count * size_of::<u64>();
            println!(
                "Composite circuit contains {} boolean gates and {} boolean wires ({} kb)",
                bool_gate_count,
                bool_wire_count,
                bool_size_est / 1024
            );
            println!(
                "Composite circuit contains {} BtoA gates ({} kb)",
                b2a_count,
                (b2a_count * size_of::<CombineOperation>()) / 1024
            );
            println!(
                "Composite circuit contains {} arithmetic gates and {} arithmetic wires ({} kb)",
                arith_gate_count,
                arith_wire_count,
                arith_size_est / 1024
            );

            bincode::serialize_into(writer, &compositor)
                .expect("Failed to write composite circuit");
            println!("Dumped composite circuit to {out_fname}");
        }
        (_, _, _) => {
            println!("Usage: -a [arithmetic circuit file] -b [boolean circuit file] -c [connection circuit file] -w [witness] -o [output file]")
        }
    }
}

type B2A = Vec<(usize, Vec<usize>)>;
type BoolTrans = HashMap<usize, usize>;
type ArithTrans = HashMap<usize, usize>;

fn read_connection_circuit(
    reader: BufReader<File>,
    top_files: (String, String),
    hashers: (WireHasher, WireHasher),
) -> (B2A, BoolTrans, ArithTrans) {
    let (bool_top, arith_top) = top_files;
    let (mut bool_hasher, mut arith_hasher) = hashers;

    let mut b2a: B2A = Vec::new();
    let mut bool_trans: BoolTrans = HashMap::new();
    let mut arith_trans: ArithTrans = HashMap::new();

    for line in reader.lines().flatten() {
        let mut line: VecDeque<&str> = line.trim().split(' ').collect();
        let cmd = line.pop_front().unwrap();
        match cmd {
            ".model" => {
                println!("Reading connection circuit: {}", line.pop_front().unwrap());
            }
            ".gate" => {
                let op = line.pop_front().unwrap().to_ascii_lowercase();
                match op.as_str() {
                    "btoa" => {
                        let (_, out) = parse_split(line.pop_front().unwrap());
                        let inputs = drain_inputs(line)
                            .drain(..)
                            .map(|t| bool_hasher.get_wire_id(t))
                            .collect();
                        b2a.push((arith_hasher.get_wire_id(out), inputs));
                    }
                    bool_name if (bool_name == bool_top) => {
                        for (local_wire, conn_wire) in line.drain(..).map(parse_split) {
                            bool_trans.insert(
                                bool_hasher.get_wire_id(conn_wire),
                                bool_hasher.get_wire_id(local_wire),
                            );
                        }
                    }
                    arith_name if (arith_name == arith_top) => {
                        for (local_wire, conn_wire) in line.drain(..).map(parse_split) {
                            arith_trans.insert(
                                arith_hasher.get_wire_id(conn_wire),
                                arith_hasher.get_wire_id(local_wire),
                            );
                        }
                    }
                    _ => {
                        unimplemented!(
                            "We don't know how to handle {} gates in the connection circuit yet",
                            op
                        )
                    }
                }
            }
            ".subckt" => {
                panic!("No subcircuits allowed in the connection circuit, sorry!")
            }
            _ => (),
        }
    }

    (b2a, bool_trans, arith_trans)
}

fn drain_inputs(mut line: VecDeque<&str>) -> Vec<&str> {
    line.drain(..).map(|part| parse_split(part).1).collect()
}
