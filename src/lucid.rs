mod optimize;

use optimize::*;

use std::fs::File;
use std::io::{BufReader, BufWriter};

use clap::{App, Arg};

use mcircuit::largest_wires;
use optimize::isolate::*;
use std::cmp::max;

fn main() {
    let matches = App::new("Lucid")
        .version("0.1")
        .author("Mathias Hall-Andersen <mathias@hall-andersen.dk>")
        .about("Optimizes circuits in Bristol format.")
        .arg(
            Arg::with_name("circuit-in")
                .long("in")
                .help("The path to the file containing the input circuit")
                .empty_values(false)
                .required(true),
        )
        .arg(
            Arg::with_name("circuit-out")
                .long("out")
                .help("The path to the file containing the resulting circuit")
                .empty_values(false)
                .required(true),
        )
        .get_matches();

    let path_in = matches.value_of("circuit-in").unwrap();
    let path_out = matches.value_of("circuit-out").unwrap();

    println!("loading circuit...");
    let file = File::open(path_in).unwrap();
    let mut reader = BufReader::new(file);
    let circuit = bin::load_serialized(&mut reader).unwrap();

    let circuit = combine_arithmetic_namespace(circuit);

    let (largest_arith, largest_bool) = largest_wires(&circuit);
    let n_wires = max(largest_bool, largest_arith);

    println!("dead code elimination...");
    // let circuit = dead::eliminate_dead_code(&circuit, n_wires);

    println!("register allocation...");
    let circuit = ram::register_aliasing(&circuit, n_wires);

    let mut circuit = isolate_arithmetic_wires(circuit);

    insert_size_hint(&mut circuit);

    println!("dumping to file...");
    let file = File::create(path_out).unwrap();
    let mut writer = BufWriter::new(file);
    bin::store_serialized(&mut writer, &circuit).unwrap();
}
