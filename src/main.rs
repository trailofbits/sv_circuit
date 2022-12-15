use std::collections::{HashMap, VecDeque};
use std::fs::{read_to_string, File};
use std::io::{prelude::*, BufReader, BufWriter};

use clap::{App, Arg};
use mcircuit::exporters::{BristolFashion, Export, IR0, IR1};
use mcircuit::parsers::blif::{parse_split, BlifParser};
use mcircuit::parsers::WireHasher;
use mcircuit::{CombineOperation, Operation, Parse};

use std::io;
use std::mem::size_of;
use sv_circuit::CircuitCompositor;

fn emit_ir0(out_fname: &str, witness: &[bool]) -> Result<(), io::Error> {
    // write witness.
    let witness_fname = format!("{}.private_input", out_fname);
    let mut witness_writer =
        BufWriter::new(File::create(witness_fname).expect("Failed to open output file"));
    IR0::export_private_input(witness, &mut witness_writer).expect("Failed to write private input");

    // write instance.
    let instance_fname = format!("{}.public_input", out_fname);
    let mut instance_writer =
        BufWriter::new(File::create(instance_fname).expect("Failed to open output file"));
    IR0::export_public_input(None, &mut instance_writer).expect("Failed to write public input");

    Ok(())
}

/// Rust version of circuit compositor
fn main() {
    let matches = App::new("sv-compositor (Rusty)")
        .version(env!("CARGO_PKG_VERSION"))
        .author("Eric Hennenfent <eric.hennenfent@trailofbits.com>")
        .about(
            "Converts circuits in the BLIF circuit format to composite boolean/arithmetic circuits",
        )
        .arg(
            Arg::with_name("arithmetic_circuit")
                .short("a")
                .long("arithmetic_circuit")
                .takes_value(true)
                .help("BLIF File"),
        )
        .arg(
            Arg::with_name("boolean_circuit")
                .short("b")
                .long("boolean_circuit")
                .takes_value(true)
                .help("BLIF File"),
        )
        .arg(
            Arg::with_name("connection_circuit")
                .short("c")
                .long("connection_circuit")
                .takes_value(true)
                .help("Connection circuit file"),
        )
        .arg(
            Arg::with_name("witness")
                .short("w")
                .takes_value(true)
                .help("Witness trace (length 560)"),
        )
        .arg(
            Arg::with_name("output_file")
                .short("o")
                .long("output_file")
                .takes_value(true)
                .required(true)
                .help("Compiled circuit"),
        )
        .get_matches();

    let out_fname = matches.value_of("output_file").unwrap();

    let maybe_arith = matches.value_of("arithmetic_circuit");
    let maybe_bool = matches.value_of("boolean_circuit");
    let maybe_conn = matches.value_of("connection_circuit");
    let maybe_witness = matches.value_of("witness");

    // compilation target determined by output file extension.
    let export_bristol = out_fname.ends_with("bristol");
    let export_ir0 = out_fname.ends_with("circuit");
    let export_ir1 = out_fname.ends_with("ir1");

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

            let witness = maybe_witness.expect("no witness for Bristol circuit!");
            let w: Vec<bool> = read_to_string(witness)
                .expect("failed to open witness")
                .trim()
                .chars()
                .filter(|&c| c != '\n')
                .map(|c| match c {
                    '0' => false,
                    '1' => true,
                    _ => panic!("bad bit {:?} in witness!", c),
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
                .and(emit_ir0(out_fname, &w)),
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
            println!("Dumped composite circuit to {}", out_fname);
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
