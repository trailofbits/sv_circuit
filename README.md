# sv_circuit

[![Build Status](https://github.com/trailofbits/sv_circuit/actions/workflows/ci.yml/badge.svg)](https://github.com/trailofbits/sholva/actions?query=workflow%3ACI)

SIEVE circuit compositor.

## Dependencies

Built using [nix](https://nixos.wiki/wiki/Nix_package_manager).
Follow the upstream [nix installation instructions](https://nixos.org/download.html).

## Building

```bash
$ nix-shell --pure --run "make"
```

> NOTE: `nix-shell` invocations interact poorly with, e.g., the [fish shell](https://fishshell.com/).
> Use a [Development Environment](#devlopment-environment) to run the quoted command, or drop into bash temporarily.

## Installing

```bash
$ nix-shell --pure --run "make install"
```

## Testing

```bash
$ nix-shell --pure --run "make test"
```

## Development Environment

To enter a shell with all dependencies,

```bash
$ nix-shell
```

Or a shell with _only_ the dependencies (eliminating any system-specifics):

```bash
$ nix-shell --pure
```

## Distribution and Licensing

The views, opinions, and/or findings expressed are those of the author(s) and
should not be interpreted as representing the official views or policies of the
Department of Defense or the U.S. Government.

_sv_circuit_ is licensed under the GNU AGPLv3 License. A copy of the terms can
be found in the [LICENSE](./LICENSE) file.
