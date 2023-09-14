{ sources }:

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

  nativeBuildInputs = [
    (pkgs.rustChannelOf {
      date = "2023-06-15";
      channel = "nightly";
    }).rust
  ];

  cargoLock = {
    lockFile = ./Cargo.lock;
    outputHashes = {
      "mcircuit-0.1.10" = "sha256-ghkJHO0YQkFY/aA/t+LmY7bF9JHL5IdTfgSQbophwiw=";
    };
  };

  doCheck = true;
}
