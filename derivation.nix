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

  cargoHash = "sha256-ZQVG+V06W+4pzQBX3xGMyuxT/vSsOiS6OfdUT4VjYeQ=";
}
