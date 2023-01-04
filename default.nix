let
  rust_overlay = import (builtins.fetchTarball "https://github.com/oxalica/rust-overlay/archive/master.tar.gz");

  pkgs = import (builtins.fetchTarball {
    name = "nixpkgs-unstable-2022-07-19";
    url = "https://github.com/nixos/nixpkgs/archive/2df37941652c28e0858b9a9520ce5763c43c2ec1.tar.gz";
    sha256 = "sha256:12d5w1bvhjlxrvdhsc44gq1lv5s3z1lv18s39q1702hwmp2bz071";
  }) { overlays = [ rust_overlay ]; };

  rustVersion = "2022-10-01";
  sv-rust = pkgs.rust-bin.nightly.${rustVersion}.default.override {
    extensions = [
      "rust-src"
      "clippy"
      "rustfmt"
    ];
  };

in
with pkgs; with pkgs.python311Packages; buildPythonPackage rec {
  name = "sv-tools";
  src = ./.;

  nativeBuildInputs = [
    cacert
    git
    sv-rust
  ];

  # NOTE(jl): python dependencies are declared by externally to nix in `pyproject.toml`.
  format = "pyproject";
}
