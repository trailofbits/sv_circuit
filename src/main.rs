use std::fs::{read_to_string, File};
use std::io::{BufReader, BufWriter};
use std::path::Path;

use anyhow::{bail, Result};
use clap::{arg, command};
use mcircuit::exporters::{Export, IR0};
use mcircuit::parsers::blif::{BlifParser};
use mcircuit::{Operation, Parse};

use std::io;

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
        .arg(arg!(-b --boolean_circuit <FILE> "BLIF file"))
        .arg(arg!(-w --witness <FILE> "Witness trace"))
        .arg(arg!(-o --output_file <FILE> "Compiled circuit").required(true))
        .get_matches();

    let out_fname: &String = matches.get_one::<String>("output_file").unwrap(); // FIXME(jl): refactor clap
                                                                                // types
    let base_fname: &str = Path::new(out_fname)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap();

    let maybe_bool = matches.get_one::<String>("boolean_circuit");
    let maybe_witness = matches.get_one::<String>("witness");

    match maybe_bool {
        Some(path) => {
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

            // IR0
            IR0::export_circuit(
                &flat.into_iter().collect::<Vec<Operation<bool>>>(),
                &w,
                &mut writer,
            )
            .and(emit_ir0(base_fname, &w))?;
        }
        _ => {
            println!("Usage: -a [arithmetic circuit file] -b [boolean circuit file] -c [connection circuit file] -w [witness] -o [output file]")
        }
    }

    Ok(())
}
