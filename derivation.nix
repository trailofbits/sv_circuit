{ lib
, rustPlatform
}:

let
  sources = import ./nix/sources.nix;
  pkgs = import sources.nixpkgs
    {
      overlays = [
        (import (fetchTarball "https://github.com/oxalica/rust-overlay/archive/master.tar.gz"))
      ];
    };
  rustVersion = "2023-01-01";
  rust = pkgs.rust-bin.nightly.${rustVersion}.default.override {
    extensions = [
      "rust-src"
      "clippy"
      "rustfmt"
    ];
  };
in
rustPlatform.buildRustPackage
rec {
  pname = "sv_circuit";
  version = "0.0.1";

  src = ./.;

  nativeBuildInputs = [ rust ];
  cargoHash = "sha256-Xmls6HqE7B2YQlZmiEfKRevb6vfaPnRY5r0bTiQyneI=";
}
