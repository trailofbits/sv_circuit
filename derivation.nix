{ sources ? import ./nix/sources.nix, lib }:

let
  pkgs = import sources.nixpkgs {
    overlays = [
      (import (fetchTarball
        "https://github.com/mozilla/nixpkgs-mozilla/archive/master.tar.gz"))
    ];
  };
in with pkgs;
rustPlatform.buildRustPackage rec {
  pname = "sv_circuit";
  version = "0.0.1";

  src = ./.;

  nativeBuildInputs = [ (pkgs.rustChannelOf { date = "2023-03-01"; channel = "nightly"; }).rust ];

  cargoLock = {
    lockFile = ./Cargo.lock;
    outputHashes = {
      "mcircuit-0.1.10" = "sha256-hX88gI6SLonD5v2/jdLQNUrzVjwTJMaAV2bqfx3ACw4=";
    };
  };

  doCheck = true;
}
