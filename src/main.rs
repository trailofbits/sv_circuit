use std::collections::{HashMap, VecDeque};
use std::convert::TryInto;
use std::fs::{read_to_string, File};
use std::io::{prelude::*, BufReader, BufWriter};
use std::path::Path;

use clap::{arg, command};
use mcircuit::exporters::{BristolFashion, Export, IR0, IR1};
use mcircuit::parsers::blif::{parse_split, BlifParser};
use mcircuit::parsers::WireHasher;
use mcircuit::{CombineOperation, Operation, Parse};

use std::io;
use std::mem::size_of;
use sv_circuit::CircuitCompositor;

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

fn emit_ir0(base_fname: &str, witness: &[[bool; WITNESS_LEN]]) -> Result<(), io::Error> {
    // write witness.
    let witness_fname = format!("{base_fname}.private_input");
    let mut witness_writer =
        BufWriter::new(File::create(witness_fname).expect("Failed to open witness file"));
    IR0::export_private_input(witness, &mut witness_writer).expect("Failed to write private input");

    // write instance.
    let instance_fname = format!("{base_fname}.public_input");
    let mut instance_writer =
        BufWriter::new(File::create(instance_fname).expect("Failed to open instance file"));
    IR0::export_public_input(None, &mut instance_writer).expect("Failed to write public input");

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
                (true, false, false) => BristolFashion::export_circuit(
                    &flat.into_iter().collect::<Vec<Operation<bool>>>(),
                    &w,
                    &mut writer,
                ),
                // IR0
                (false, true, false) => IR0::export_circuit(
                    &flat.into_iter().collect::<Vec<Operation<bool>>>(),
                    &w,
                    &mut writer,
                )
                .and(emit_ir0(base_fname, &w)),
                // IR1
                (false, false, true) => IR1::export_circuit(
                    &flat.into_iter().collect::<Vec<Operation<bool>>>(),
                    &w,
                    &mut writer,
                ),
                _ => {
                    bincode::serialize_into(writer, &flat).expect("Failed to write circuit");
                    Ok(())
                }
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
