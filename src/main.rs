use std::fs::{read_to_string, File};
use std::io::{BufReader, BufWriter};
use std::path::{Path, PathBuf};

use anyhow::{bail, Result};
use clap::{command, Parser};
use mcircuit::exporters::{Export, IR0};
use mcircuit::parsers::blif::BlifParser;
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

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    #[clap(short, long, value_name = "BLIF")]
    blif: PathBuf,

    #[clap(short, long, value_name = "WITNESS")]
    witness: PathBuf,

    #[clap(short, long, value_name = "OUTPUT")]
    output: PathBuf,
}

/// Rust version of circuit compositor
fn main() -> Result<()> {
    let cli = Cli::parse();

    // Parse and process input BLIF.
    let blif = File::open(cli.blif)
        .map(BufReader::new)
        .map(BlifParser::<bool>::new)?;
    let (flat, _, _) = sv_circuit::flatten(blif);

    // Parse and process input witness.
    // FIXME(jl): move this into a `parser` module.
    let witness: Vec<bool> = read_to_string(cli.witness)?
        .trim()
        .chars()
        .filter(|&c| c != '\n')
        .flat_map(|c| match c {
            '0' => Ok(false),
            '1' => Ok(true),
            _ => bail!("bad bit {:?} in witness!", c),
        })
        .collect();

    let base_fname: &str = Path::new(&cli.output)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap();
    let statement_fname = format!("{base_fname}.circuit");
    let mut output = File::create(statement_fname).map(BufWriter::new)?;

    // IR0
    IR0::export_circuit(
        &flat.into_iter().collect::<Vec<Operation<bool>>>(),
        &witness,
        &mut output,
    )?;
    emit_ir0(base_fname, &witness)?;

    Ok(())
}
