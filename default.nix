let
  rust_overlay = import (builtins.fetchTarball "https://github.com/oxalica/rust-overlay/archive/master.tar.gz");
  pkgs = import <nixpkgs> { overlays = [ rust_overlay ]; };
  rustVersion = "2021-10-31";
  rust = pkgs.rust-bin.nightly.${rustVersion}.default.override {
    extensions = [
      "rust-src" # for rust-analyzer
    ];
  };
in
with import <nixpkgs> {};
pkgs.mkShell {
  name = "sv_circuit";

  nativeBuildInputs = [
    rust
  ];

  RUST_BACKTRACE = 1;
}
