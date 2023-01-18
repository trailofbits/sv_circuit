# sv-compositor

SIEVE circuit compositor.

## Dependencies

Built using [nix](https://nixos.wiki/wiki/Nix_package_manager).
Follow the upstream [nix installation instructions](https://nixos.org/download.html).

## Development Environment

To enter a shell with all dependencies,

```bash
$ nix-shell
```

## Building

```bash
$ nix-shell --pure --run "cargo build --release"
```

## Installing

```bash
$ nix-shell --pure --run "cargo install --path ."
```

> NOTE: the above interacts poorly with the [fish shell](https://fishshell.com/).
> Either use a development shell then run the quoted command, or drop into another shell temporarily.
