# shamefile

Turn linter suppressions from silent technical debt into reviewable, documented decisions.

```bash
npm install -g shamefile
shame me .
```

Provides the `shame` CLI — a prebuilt native binary selected automatically for your platform via npm `optionalDependencies`. No Rust toolchain required at install time.

## Supported platforms

| OS | Architecture | libc |
|---|---|---|
| Linux | x64, arm64 | glibc, musl (Alpine) |
| macOS | x64 (Intel), arm64 (Apple Silicon) | — |
| Windows | x64, arm64 | — |

Other platforms: install from source with `cargo install --git https://github.com/BKDDFS/shamefile`.

## Documentation

See the [main project README](https://github.com/BKDDFS/shamefile#readme) for usage, registry format, and CI/CD integration.

## License

Apache-2.0
