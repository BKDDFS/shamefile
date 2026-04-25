#!/usr/bin/env node
// Thin launcher: locates the platform-specific binary installed via
// optionalDependencies and execs it with the user's argv.

const { execFileSync, spawnSync } = require("node:child_process");

/**
 * Detects whether the current Linux system uses musl libc (e.g. Alpine)
 * rather than glibc (e.g. Ubuntu, Debian, RHEL).
 *
 * Both libc implementations ship a `ldd` tool, but `ldd --version` behaves
 * differently on each:
 *   - glibc: prints "ldd (GNU libc) 2.35..." to stdout and exits 0
 *   - musl:  prints "musl libc (x86_64) Version 1.2.4..." to stderr and exits 1
 *
 * We look for the substring "musl" in whichever stream produced output.
 * The catch branch handles musl's non-zero exit — execFileSync throws,
 * and err.stderr holds the banner we need to inspect.
 */
function isLinuxMusl() {
  try {
    const out = execFileSync("ldd", ["--version"], { stdio: ["pipe", "pipe", "pipe"] });
    return out.toString().includes("musl");
  } catch (err) {
    return String(err.stderr ?? "").includes("musl");
  }
}

const platformMap = {
  "linux-x64":        { pkg: "shamefile-linux-x64",        bin: "shame" },
  "linux-arm64":      { pkg: "shamefile-linux-arm64",      bin: "shame" },
  "linux-x64-musl":   { pkg: "shamefile-linux-x64-musl",   bin: "shame" },
  "linux-arm64-musl": { pkg: "shamefile-linux-arm64-musl", bin: "shame" },
  "darwin-x64":       { pkg: "shamefile-darwin-x64",       bin: "shame" },
  "darwin-arm64":     { pkg: "shamefile-darwin-arm64",     bin: "shame" },
  "win32-x64":        { pkg: "shamefile-windows-x64",      bin: "shame.exe" },
  "win32-arm64":      { pkg: "shamefile-windows-arm64",    bin: "shame.exe" },
};

const base = `${process.platform}-${process.arch}`;
const key = process.platform === "linux" && isLinuxMusl() ? `${base}-musl` : base;
const entry = platformMap[key];

if (!entry) {
  const supported = Object.keys(platformMap).join(", ");
  console.error(
    `shamefile: unsupported platform ${key}. Supported: ${supported}.\n` +
      `Install from source: cargo install --git https://github.com/BKDDFS/shamefile`,
  );
  process.exit(1);
}

let binaryPath;
try {
  binaryPath = require.resolve(`${entry.pkg}/bin/${entry.bin}`);
} catch {
  console.error(
    `shamefile: platform package "${entry.pkg}" is not installed. ` +
      `This usually means npm skipped it during install. ` +
      `Try: npm install ${entry.pkg}@$(npm view shamefile version)`,
  );
  process.exit(1);
}

const result = spawnSync(binaryPath, process.argv.slice(2), {
  stdio: "inherit",
});

if (result.error) {
  console.error(`shamefile: failed to execute ${binaryPath}: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
