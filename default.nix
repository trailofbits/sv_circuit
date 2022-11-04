let
  rust_overlay = import (builtins.fetchTarball "https://github.com/oxalica/rust-overlay/archive/master.tar.gz");
  pkgs = import <nixpkgs> { overlays = [ rust_overlay ]; };
  rustVersion = "2021-10-24";
  rust = pkgs.rust-bin.nightly.${rustVersion}.default.override {
    extensions = [
      "rust-src"
      "clippy"
    ];
  };
in
with pkgs; stdenv.mkDerivation {
  name = "sv_circuit";
  src = ./.;

  nativeBuildInputs = [
    cacert
    git
    rust
  ];
}
