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

          # NOTE(jl): as of 2023-07-02, `impl trait` feature is currently
          # nightly only. Pin to `pkgs.rust-bin.beta.latest.default` with future release.
          nativeBuildInputs = [
            (pkgs.rustChannelOf {
              date = "2023-03-01";
              channel = "nightly";
            }).rust
          ];
        in rec {
          default = sv_circuit;
          sv_circuit = pkgs.rustPlatform.buildRustPackage rec {
            pname = "sv_circuit";
            version = "0.0.1";

            src = ./.;
            inherit nativeBuildInputs;

            cargoLock = {
              lockFile = ./Cargo.lock;
              outputHashes = {
                "mcircuit-0.1.10" =
                  "sha256-ghkJHO0YQkFY/aA/t+LmY7bF9JHL5IdTfgSQbophwiw=";
              };
            };

            doCheck = true;
            meta = with lib; {
              description = "Zero-knowledge proofs for i386 program execution";
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
