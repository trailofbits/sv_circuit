{ sources ? import ./nix/sources.nix
, pkgs ? import sources.nixpkgs {
    overlays = [
      (import (fetchTarball "https://github.com/oxalica/rust-overlay/archive/master.tar.gz"))
    ];
  }
}:

let
  sv_circuit = pkgs.callPackage ./derivation.nix { };
  rustVersion = "2023-01-01";
  rust = pkgs.rust-bin.nightly.${rustVersion}.default.override {
    extensions = [
      "rust-src"
      "clippy"
      "rustfmt"
    ];
  };
in
with pkgs; stdenv.mkDerivation {
  name = "sv_circuit";

  nativeBuildInputs = [
    git
    rust
  ];
}
