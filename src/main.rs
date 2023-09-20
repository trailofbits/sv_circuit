use std::collections::{HashMap, VecDeque};
use std::fs::{read_to_string, File};
use std::io::{prelude::*, BufReader, BufWriter};
use std::path::Path;

use anyhow::{bail, Result};
use clap::{arg, command};
use mcircuit::exporters::{BristolFashion, Export, IR0, IR1};
use mcircuit::parsers::blif::{parse_split, BlifParser};
use mcircuit::parsers::WireHasher;
use mcircuit::{CombineOperation, Operation, Parse};

use std::io;
use std::mem::size_of;
use sv_circuit::CircuitCompositor;

fn emit_ir0(base_fname: &str, witness: &[bool]) -> Result<(), io::Error> {
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
fn main() -> Result<()> {
    let matches = command!()
        .arg(arg!(-a --arithmetic_circuit <FILE> "BLIF file"))
        .arg(arg!(-b --boolean_circuit <FILE> "BLIF file"))
        .arg(arg!(-c --connection_circuit <FILE> "Connection circuit file"))
        .arg(arg!(-w --witness <FILE> "Witness trace"))
        .arg(arg!(-o --output_file <FILE> "Compiled circuit").required(true))
        .get_matches();

    let out_fname: &String = matches.get_one::<String>("output_file").unwrap(); // FIXME(jl): refactor clap
                                                                                // types
    let base_fname: &str = Path::new(out_fname)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap();

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
            let reader = File::open(path).map(BufReader::new)?;
            let (flat, _, _) = sv_circuit::flatten(BlifParser::<u64>::new(reader));
            let writer = File::create(out_fname).map(BufWriter::new)?;
            bincode::serialize_into(writer, &flat)?;
        }
        (None, Some(path), None) => {
            let reader = File::open(path).map(BufReader::new)?;
            let (flat, _, _) = sv_circuit::flatten(BlifParser::<bool>::new(reader));

            let mut writer = File::create(out_fname).map(BufWriter::new)?;

            let witness = maybe_witness.expect("no witness for Bristol circuit!");
            let w: Vec<bool> = read_to_string(witness)?
                .trim()
                .chars()
                .filter(|&c| c != '\n')
                .flat_map(|c| match c {
                    '0' => Ok(false),
                    '1' => Ok(true),
                    _ => bail!("bad bit {:?} in witness!", c),
                })
                .collect();

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
                    bincode::serialize_into(writer, &flat)?;
                    Ok(())
                }
            }?;
        }
        (Some(arith_path), Some(bool_path), Some(conn_path)) => {
            let bool_reader = File::open(bool_path).map(BufReader::new)?;
            let (flat_bool, top_bool, hasher_bool) =
                sv_circuit::flatten(BlifParser::<bool>::new(bool_reader));

            let arith_reader = BufReader::new(File::open(arith_path)?);
            let (flat_arith, top_arith, hasher_arith) =
                sv_circuit::flatten(BlifParser::<u64>::new(arith_reader));

            let mut compositor = CircuitCompositor::new(flat_bool, flat_arith);

            let conn_reader = BufReader::new(File::open(conn_path)?);
            let (b2a, bool_translations, arith_translations) = read_connection_circuit(
                conn_reader,
                (top_bool, top_arith),
                (hasher_bool, hasher_arith),
            );

            for (arith_untrans, mut bool_untrans) in b2a {
                let arith_trans: &usize = arith_translations.get(&arith_untrans).unwrap(); // FIXME(jl):
                                                                                           // into seemed to
                                                                                           // work here?
                let bool_trans: Vec<usize> = bool_untrans
                    .drain(..)
                    .map(|u| bool_translations.get(&u).unwrap()) // FIXME(jl)
                    .copied()
                    .collect();

                if let Some(min) = bool_trans.iter().min() {
                    compositor.connect(*arith_trans, *min)
                }
            }

            let writer = BufWriter::new(File::create(out_fname)?);

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

            bincode::serialize_into(writer, &compositor)?;
            println!("Dumped composite circuit to {out_fname}");
        }
        (_, _, _) => {
            println!("Usage: -a [arithmetic circuit file] -b [boolean circuit file] -c [connection circuit file] -w [witness] -o [output file]")
        }
    }

    Ok(())
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
