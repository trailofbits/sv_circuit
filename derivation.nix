{ sources ? import ./nix/sources.nix
, rustPlatform
}:

let
  pkgs = import sources.nixpkgs {
    overlays = [
      (import (fetchTarball "https://github.com/mozilla/nixpkgs-mozilla/archive/master.tar.gz"))
    ];
  };
in
with pkgs; rustPlatform.buildRustPackage rec {
  pname = "sv_circuit";
  version = "0.0.1";

  src = ./.;

  nativeBuildInputs = [
    git
    latest.rustChannels.nightly.rust
  ];

  cargoHash = "sha256-Xmls6HqE7B2YQlZmiEfKRevb6vfaPnRY5r0bTiQyneI=";
}
