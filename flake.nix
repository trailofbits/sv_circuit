{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.05";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-compat, rust-overlay, ... }:
    let
      supportedSystems =
        [ "x86_64-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      nixpkgsFor = forAllSystems (system: import nixpkgs { inherit system; });
    in {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgsFor.${system}.extend (import rust-overlay);
          inherit (pkgs) stdenv lib;
        in rec {
          default = sv_circuit;
          sv_circuit = with pkgs;
            let
              platform = (rustChannelOf {
                date = "2023-06-15";
                channel = "nightly";
              }).default;
            in (makeRustPlatform {
              cargo = platform;
              rustc = platform;
            }).buildRustPackage rec {
              pname = "sv_circuit";
              version = "0.0.1";

              src = ./.;

              cargoLock = {
                lockFile = ./Cargo.lock;
                outputHashes = {
                  "mcircuit-0.1.10" =
                    "sha256-MUlaG+/IdcIwqiPyv4o3r+flPpf9lzHHWAZHdMkxBjs=";
                };
              };

              doCheck = true;
              meta = with lib; {
                description =
                  "Zero-knowledge proofs for i386 program execution";
                license = licenses.agpl3Only;
              };
            };
        });

      apps = forAllSystems (system: rec {
        default = sv_circuit;
        sv_circuit = {
          type = "app";
          program = "${self.packages.${system}.sv_circuit}/bin/sv-compositor";
        };
      });
    };
}
