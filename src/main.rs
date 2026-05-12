use anyhow::{Context, Result};
use chrono::Utc;
use clap::{Parser, Subcommand};
use shamefile::registry::{Entry, Registry, content_hash};
use shamefile::scanner;
use std::collections::HashSet;
use std::path::{Path, PathBuf};

struct MatchResult {
    violation_to_entry: Vec<Option<usize>>,
    entry_to_violation: Vec<Option<usize>>,
}

fn cascade_match(
    old_entries: &[Entry],
    violations: &[scanner::Violation],
    renames: &std::collections::HashMap<String, String>,
) -> MatchResult {
    let mut v2e: Vec<Option<usize>> = vec![None; violations.len()];
    let mut e2v: Vec<Option<usize>> = vec![None; old_entries.len()];

    // Pass A: location match — covers exact match and content-changed-same-line
    for (vi, v) in violations.iter().enumerate() {
        let v_location = Entry::make_location(&v.path.to_string_lossy(), v.line_number);
        if let Some(oi) = old_entries.iter().enumerate().find_map(|(i, e)| {
            if e2v[i].is_none() && e.location == v_location && e.token == v.matched_token {
                Some(i)
            } else {
                None
            }
        }) {
            v2e[vi] = Some(oi);
            e2v[oi] = Some(vi);
        }
    }

    // Pass B: content hash match — covers line shift (same content, different line)
    // Also handles renames: if entry's file was renamed, match against the new file name.
    for (vi, v) in violations.iter().enumerate() {
        if v2e[vi].is_some() {
            continue;
        }
        let v_file = v.path.to_string_lossy();
        let v_hash = content_hash(&v.line_content);
        if let Some(oi) = old_entries.iter().enumerate().find_map(|(i, e)| {
            if e2v[i].is_none() && e.content == v_hash && e.token == v.matched_token {
                let file_matches = e.file() == v_file.as_ref()
                    || renames
                        .get(e.file())
                        .is_some_and(|new| new == v_file.as_ref());
                if file_matches { Some(i) } else { None }
            } else {
                None
            }
        }) {
            v2e[vi] = Some(oi);
            e2v[oi] = Some(vi);
        }
    }

    MatchResult {
        violation_to_entry: v2e,
        entry_to_violation: e2v,
    }
}

fn is_entry_in_scope(
    entry: &Entry,
    scanned_files: &HashSet<PathBuf>,
    skipped_files: &HashSet<PathBuf>,
    scan_paths_canonical: &[PathBuf],
    registry_dir_canonical: &Path,
) -> bool {
    let entry_file_raw = PathBuf::from(entry.file());
    let entry_file = if entry_file_raw.is_absolute() {
        strip_registry_prefix(&entry_file_raw, registry_dir_canonical).unwrap_or(entry_file_raw)
    } else {
        entry_file_raw
    };
    if scanned_files.contains(&entry_file) {
        true
    } else if skipped_files.contains(&entry_file) {
        false
    } else {
        scan_paths_canonical
            .iter()
            .any(|sp| entry_file.starts_with(sp))
    }
}

fn strip_registry_prefix(path: &Path, registry_dir_canonical: &Path) -> Option<PathBuf> {
    path.strip_prefix(registry_dir_canonical)
        .map(|p| p.to_path_buf())
        .ok()
        .or_else(|| strip_registry_prefix_fallback(path, registry_dir_canonical))
}

#[cfg(windows)]
fn strip_registry_prefix_fallback(path: &Path, registry_dir_canonical: &Path) -> Option<PathBuf> {
    let path = strip_windows_verbatim_prefix(path);
    let registry_dir = strip_windows_verbatim_prefix(registry_dir_canonical);
    path.strip_prefix(registry_dir)
        .map(|p| p.to_path_buf())
        .ok()
}

#[cfg(not(windows))]
fn strip_registry_prefix_fallback(_path: &Path, _registry_dir_canonical: &Path) -> Option<PathBuf> {
    None
}

#[cfg(windows)]
fn strip_windows_verbatim_prefix(path: &Path) -> PathBuf {
    use std::path::{Component, Prefix};

    let mut components = path.components();
    if let Some(Component::Prefix(prefix)) = components.next() {
        match prefix.kind() {
            Prefix::VerbatimDisk(drive) => {
                let mut normalized = PathBuf::from(format!("{}:", drive as char));
                normalized.extend(components);
                normalized
            }
            Prefix::VerbatimUNC(server, share) => {
                let mut normalized = PathBuf::from(r"\\");
                normalized.push(server);
                normalized.push(share);
                normalized.extend(components);
                normalized
            }
            _ => path.to_path_buf(),
        }
    } else {
        path.to_path_buf()
    }
}

#[derive(Parser)]
#[command(name = "shame")]
#[command(version)]
#[command(about = "A tool to enforce documentation for code suppressions", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Scan for suppressions, sync registry, and validate
    Me {
        /// Paths to scan
        #[arg(default_value = ".")]
        paths: Vec<PathBuf>,

        /// Read-only validation for CI/CD (never saves)
        #[arg(short = 'n', long)]
        dry_run: bool,

        /// Also scan hidden files and directories (dotfiles)
        #[arg(long)]
        hidden: bool,
    },

    /// Show the next undocumented suppression
    Next {
        /// Document this entry with the given reason
        reason: Option<String>,
    },

    /// Document a specific suppression with a reason
    Fix {
        /// Location (e.g. "./src/foo.py:42")
        location: String,

        /// Token (e.g. "# noqa")
        token: String,

        /// The reason for the suppression
        #[arg(long)]
        why: String,
    },

    /// Remove a specific suppression entry from the registry
    #[command(alias = "rm")]
    Remove {
        /// Location (e.g. "./src/foo.py:42")
        location: String,

        /// Token (e.g. "# noqa")
        token: String,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Me {
            paths,
            dry_run,
            hidden,
        } => {
            handle_me(&paths, dry_run, hidden)?;
        }
        Commands::Next { reason } => {
            handle_next(reason.as_deref())?;
        }
        Commands::Fix {
            location,
            token,
            why,
        } => {
            handle_fix(&location, &token, &why)?;
        }
        Commands::Remove { location, token } => {
            handle_remove(&location, &token)?;
        }
    }
    Ok(())
}

fn handle_me(scan_paths: &[PathBuf], dry_run: bool, hidden: bool) -> Result<()> {
    // 1. Validate that all paths exist (fail-fast)
    for path in scan_paths {
        if !path.exists() {
            eprintln!("Error: path does not exist: {}", path.display());
            std::process::exit(1);
        }
    }

    // 2. Determine registry location: git root or CWD
    let cwd = std::env::current_dir().context("Failed to get current directory")?;
    let registry_dir = shamefile::git::find_git_root(&cwd).unwrap_or_else(|| cwd.clone());
    let registry_dir_canonical = std::fs::canonicalize(&registry_dir)
        .context("Failed to canonicalize registry directory")?;

    // 3. Validate that all paths are within project root
    for path in scan_paths {
        if let Ok(canonical) = std::fs::canonicalize(path)
            && !canonical.starts_with(&registry_dir_canonical)
        {
            eprintln!(
                "Error: path '{}' is outside project root ({})",
                path.display(),
                registry_dir.display()
            );
            std::process::exit(1);
        }
    }

    let config_path = registry_dir.join("shamefile.yaml");

    // 4. Dispatch
    if dry_run {
        handle_dry_run(
            scan_paths,
            &config_path,
            &registry_dir,
            &registry_dir_canonical,
            hidden,
        )
    } else {
        handle_normal(
            scan_paths,
            &config_path,
            &registry_dir,
            &registry_dir_canonical,
            hidden,
        )
    }
}

struct NormalizedScanData {
    violations: Vec<scanner::Violation>,
    scanned_files: HashSet<PathBuf>,
    skipped_files: HashSet<PathBuf>,
}

/// Normalizes paths relative to `registry_dir_canonical`. Caller is responsible
/// for canonicalizing the registry dir up front (handle_me does this).
fn filter_and_normalize(
    violations: Vec<scanner::Violation>,
    scanned_files: HashSet<PathBuf>,
    skipped_files: HashSet<PathBuf>,
    registry_dir_canonical: &Path,
) -> NormalizedScanData {
    let normalized_violations = violations
        .into_iter()
        .filter_map(|mut v| {
            let v_canonical = std::fs::canonicalize(&v.path).ok()?;
            let relative = v_canonical.strip_prefix(registry_dir_canonical).ok()?;
            v.path = PathBuf::from("./").join(relative);
            Some(v)
        })
        .collect();

    let normalize_paths = |files: HashSet<PathBuf>| -> HashSet<PathBuf> {
        files
            .into_iter()
            .filter_map(|f| {
                let f_canonical = std::fs::canonicalize(&f).ok()?;
                f_canonical
                    .strip_prefix(registry_dir_canonical)
                    .ok()
                    .map(|r| PathBuf::from("./").join(r))
            })
            .collect()
    };

    NormalizedScanData {
        violations: normalized_violations,
        scanned_files: normalize_paths(scanned_files),
        skipped_files: normalize_paths(skipped_files),
    }
}

fn handle_normal(
    scan_paths: &[PathBuf],
    config_path: &Path,
    registry_dir: &Path,
    registry_dir_canonical: &Path,
    hidden: bool,
) -> Result<()> {
    // 1. Load or create registry
    let is_first_run = !config_path.exists();
    let mut registry = if is_first_run {
        println!("Creating new registry at {}", config_path.display());
        Registry::new()
    } else {
        Registry::load(config_path).context("Failed to load registry")?
    };

    // 2. Scan for violations
    let mut all_violations = Vec::new();
    let mut all_scanned_files = HashSet::new();
    let mut all_skipped_files = HashSet::new();
    for path in scan_paths {
        println!("Scanning {} for suppressions...", path.display());
        let result = scanner::scan(path, hidden).context("Failed to scan files")?;
        all_violations.extend(result.violations);
        all_scanned_files.extend(result.scanned_files);
        all_skipped_files.extend(result.skipped_files);
    }
    let scan_data = filter_and_normalize(
        all_violations,
        all_scanned_files,
        all_skipped_files,
        registry_dir_canonical,
    );
    let mut violations = scan_data.violations;
    let scanned_files = scan_data.scanned_files;
    let skipped_files = scan_data.skipped_files;
    for f in &skipped_files {
        println!("Skipped unreadable file: {}", f.display());
    }
    violations.sort_by(|a, b| {
        (&a.path, a.line_number, &a.matched_token).cmp(&(&b.path, b.line_number, &b.matched_token))
    });
    violations.dedup_by(|a, b| {
        a.path == b.path && a.line_number == b.line_number && a.matched_token == b.matched_token
    });

    // 3. Cascade matching: reconcile violations with existing entries
    let renames = shamefile::git::detect_renames(registry_dir);
    let matches = cascade_match(&registry.entries, &violations, &renames);
    let old_entries = std::mem::take(&mut registry.entries);

    let scan_paths_canonical: Vec<PathBuf> = scan_paths
        .iter()
        .filter_map(|p| std::fs::canonicalize(p).ok())
        .filter_map(|c| {
            c.strip_prefix(registry_dir_canonical)
                .ok()
                .map(|r| r.to_path_buf())
        })
        .collect();

    let mut new_entries_count = 0;
    let mut removed_count = 0;
    let mut errors_found = false;

    // 3a. Build entries from matched violations (preserve metadata, update location/content)
    for (vi, v) in violations.iter().enumerate() {
        let v_path_str = v.path.to_string_lossy().to_string();
        let new_location = Entry::make_location(&v_path_str, v.line_number);
        let new_sv = content_hash(&v.line_content);

        if let Some(oi) = matches.violation_to_entry[vi] {
            let old = &old_entries[oi];
            registry.entries.push(Entry {
                location: new_location,
                token: v.matched_token.clone(),
                content: new_sv,
                owner: old.owner.clone(),
                created_at: old.created_at,
                why: old.why.clone(),
            });
        } else {
            // New entry — no match in old registry
            registry.entries.push(Entry {
                location: new_location,
                token: v.matched_token.clone(),
                content: new_sv,
                owner: if is_first_run {
                    shamefile::git::get_git_blame_author(&v_path_str, v.line_number, registry_dir)
                        .unwrap_or_else(|| shamefile::git::get_git_current_user(registry_dir))
                } else {
                    shamefile::git::get_git_current_user(registry_dir)
                },
                created_at: Utc::now(),
                why: String::new(),
            });
            new_entries_count += 1;
            errors_found = true;
        }
    }

    // 3b. Handle unmatched old entries
    let mut unmatched_stale = Vec::new();
    for (oi, old) in old_entries.iter().enumerate() {
        if matches.entry_to_violation[oi].is_some() {
            continue; // already handled above
        }
        let in_scope = is_entry_in_scope(
            old,
            &scanned_files,
            &skipped_files,
            &scan_paths_canonical,
            registry_dir_canonical,
        );
        let entry_file_raw = PathBuf::from(old.file());
        let entry_file_normalized = if entry_file_raw.is_absolute() {
            strip_registry_prefix(&entry_file_raw, registry_dir_canonical).unwrap_or(entry_file_raw)
        } else {
            entry_file_raw
        };
        // If file was renamed, use the new name for scanned_files/violations checks
        let effective_file = renames
            .get(old.file())
            .map(PathBuf::from)
            .unwrap_or(entry_file_normalized);
        if !in_scope {
            // Out of scan scope — preserve unchanged
            registry.entries.push(old.clone());
        } else if scanned_files.contains(&effective_file) {
            // File was scanned (or its rename target was). Check if any violation
            // in this file has the same token.
            let has_token_in_file = violations
                .iter()
                .any(|v| v.path == effective_file && v.matched_token == old.token);
            if has_token_in_file {
                // Token still exists in file but cascade didn't match — line and content both changed
                unmatched_stale.push(old.clone());
            } else {
                // Token completely gone from file — safe to auto-remove
                println!("Removing stale entry: {} at {}", old.token, old.location);
                removed_count += 1;
            }
        } else {
            // File deleted or gitignored — safe to auto-remove
            println!("Removing stale entry: {} at {}", old.token, old.location);
            removed_count += 1;
        }
    }

    if !unmatched_stale.is_empty() {
        println!("Could not match these entries to current code — please review manually:");
        for e in &unmatched_stale {
            println!("  - {} at {}", e.token, e.location);
        }
        // Keep them in registry — user must resolve manually
        registry.entries.extend(unmatched_stale);
        errors_found = true;
    }

    // 4. Check for missing justifications (count before save)
    let missing_why_count = registry
        .entries
        .iter()
        .filter(|e| e.why.trim().is_empty())
        .count();
    if missing_why_count > 0 {
        errors_found = true;
    }

    // 5. Save registry
    registry
        .save(config_path)
        .context("Failed to save registry")?;

    // 6. Print summary
    if new_entries_count > 0 {
        println!(
            "Added {} new entries to {}",
            new_entries_count,
            config_path.display()
        );
    }
    if removed_count > 0 {
        println!(
            "Removed {} stale entries from {}",
            removed_count,
            config_path.display()
        );
        errors_found = true;
    }

    if missing_why_count > 0 {
        println!(
            "{} suppressions need documentation (why).",
            missing_why_count
        );
        println!(
            "Run `shame next` to see the first one, or `shame next \"<reason>\"` to fill its why."
        );
        println!();
        println!(
            "STOP — message for LLM agents: do NOT read shamefile.yaml directly. It grows large and will pollute your context for no benefit."
        );
        println!(
            "Walk entries one at a time with `shame next`, or document a specific one via `shame fix <location> <token> --why \"<reason>\"`."
        );
    }

    if errors_found {
        std::process::exit(1);
    }

    println!("Validation passed. No shame today!");

    Ok(())
}

fn handle_dry_run(
    scan_paths: &[PathBuf],
    config_path: &Path,
    registry_dir: &Path,
    registry_dir_canonical: &Path,
    hidden: bool,
) -> Result<()> {
    // 1. Load existing registry (fail if missing)
    if !config_path.exists() {
        eprintln!(
            "Registry not found at {}. Run `shame me` first to create it.",
            config_path.display()
        );
        std::process::exit(1);
    }
    let registry = Registry::load(config_path).context("Failed to load registry")?;

    // 2. Scan for violations
    let mut all_violations = Vec::new();
    let mut all_scanned_files = HashSet::new();
    let mut all_skipped_files = HashSet::new();
    for path in scan_paths {
        println!("Step 1: Scanning {} for suppressions...", path.display());
        let result = scanner::scan(path, hidden).context("Failed to scan files")?;
        all_violations.extend(result.violations);
        all_scanned_files.extend(result.scanned_files);
        all_skipped_files.extend(result.skipped_files);
    }
    let scan_data = filter_and_normalize(
        all_violations,
        all_scanned_files,
        all_skipped_files,
        registry_dir_canonical,
    );
    let mut violations = scan_data.violations;
    let scanned_files = scan_data.scanned_files;
    let skipped_files = scan_data.skipped_files;
    for f in &skipped_files {
        println!("Skipped unreadable file: {}", f.display());
    }
    violations.sort_by(|a, b| {
        (&a.path, a.line_number, &a.matched_token).cmp(&(&b.path, b.line_number, &b.matched_token))
    });
    violations.dedup_by(|a, b| {
        a.path == b.path && a.line_number == b.line_number && a.matched_token == b.matched_token
    });

    println!("Found {} suppressions in code.", violations.len());

    let mut failed = false;

    // Use cascade matching for coverage and stale checks
    let renames = shamefile::git::detect_renames(registry_dir);
    let matches = cascade_match(&registry.entries, &violations, &renames);

    // Step 2: Coverage check (code ⊆ registry)
    println!("\nStep 2: Checking coverage (code -> shamefile)...");
    let undocumented: Vec<_> = violations
        .iter()
        .enumerate()
        .filter(|(vi, _)| matches.violation_to_entry[*vi].is_none())
        .map(|(_, v)| v)
        .collect();

    if undocumented.is_empty() {
        println!("OK: All code suppressions are registered.");
    } else {
        println!(
            "FAIL: Found {} undocumented suppressions:",
            undocumented.len()
        );
        for v in &undocumented {
            println!(
                "  - {} at {}:{}",
                v.matched_token,
                v.path.display(),
                v.line_number
            );
        }
        failed = true;
    }

    // Step 3: Stale check (registry ⊆ code, scoped to scanned files)
    println!("\nStep 3: Checking for stale entries (shamefile -> code)...");
    let scan_paths_canonical: Vec<PathBuf> = scan_paths
        .iter()
        .filter_map(|p| std::fs::canonicalize(p).ok())
        .filter_map(|c| {
            c.strip_prefix(registry_dir_canonical)
                .ok()
                .map(|r| r.to_path_buf())
        })
        .collect();
    let stale: Vec<_> = registry
        .entries
        .iter()
        .enumerate()
        .filter(|(oi, e)| {
            if matches.entry_to_violation[*oi].is_some() {
                return false; // matched by cascade
            }
            is_entry_in_scope(
                e,
                &scanned_files,
                &skipped_files,
                &scan_paths_canonical,
                registry_dir_canonical,
            )
        })
        .map(|(_, e)| e)
        .collect();

    if stale.is_empty() {
        println!("OK: No stale entries.");
    } else {
        println!("FAIL: Found {} stale entries:", stale.len());
        for e in &stale {
            println!("  - {} at {} (not in code anymore)", e.token, e.location);
        }
        failed = true;
    }

    // Step 4: Justification check
    println!("\nStep 4: Checking reasons...");
    let missing_why: Vec<_> = registry
        .entries
        .iter()
        .filter(|e| e.why.trim().is_empty())
        .collect();

    if missing_why.is_empty() {
        println!("OK: All entries have reasons.");
    } else {
        println!(
            "FAIL: Found {} entries without reason (why):",
            missing_why.len()
        );
        for e in &missing_why {
            println!("  - {} at {}", e.token, e.location);
        }
        failed = true;
    }

    if failed {
        println!("\nValidation failed! Run `shame me` locally to sync.");
        std::process::exit(1);
    } else {
        println!("\nAll checks passed!");
    }

    Ok(())
}

fn find_registry_path() -> Result<PathBuf> {
    let cwd = std::env::current_dir().context("Failed to get current directory")?;
    let registry_dir = shamefile::git::find_git_root(&cwd).unwrap_or_else(|| cwd.clone());
    let config_path = registry_dir.join("shamefile.yaml");
    if !config_path.exists() {
        eprintln!(
            "Registry not found at {}. Run `shame me` first to create it.",
            config_path.display()
        );
        std::process::exit(1);
    }
    Ok(config_path)
}

fn print_entry_snippet(entry: &Entry, registry_dir: &Path) {
    println!("{}", entry.location);

    let file_path = registry_dir.join(entry.file());
    if let Ok(source) = std::fs::read_to_string(&file_path) {
        let line_num = entry.line() as usize;
        if let Some(line) = source.lines().nth(line_num - 1) {
            let trimmed = line.trim_start();
            println!("    |");
            println!("{:>4}| {}", line_num, trimmed);
            if let Some(col) = trimmed.rfind(&entry.token) {
                let underline = " ".repeat(col) + &"^".repeat(entry.token.len());
                println!("    | {underline}");
            }
        }
    }
}

fn print_remaining(remaining: usize) {
    if remaining == 0 {
        println!("All entries documented. No shame today!");
    } else {
        println!("{} entries remaining.", remaining);
    }
}

fn handle_next(fix: Option<&str>) -> Result<()> {
    // Validate reason: must be non-empty and not just whitespace
    if let Some(reason) = fix
        && reason.trim().is_empty()
    {
        eprintln!("Error: reason cannot be empty or whitespace-only.");
        std::process::exit(1);
    }

    let config_path = find_registry_path()?;
    let mut registry = Registry::load(&config_path).context("Failed to load registry")?;
    let registry_dir = config_path.parent().unwrap_or_else(|| Path::new("."));

    let entry_idx = registry
        .entries
        .iter()
        .position(|e| e.why.trim().is_empty());

    let Some(idx) = entry_idx else {
        println!("No entries need documentation. No shame today!");
        return Ok(());
    };

    if let Some(reason) = fix {
        println!(
            "Documented: {} at {}",
            registry.entries[idx].token, registry.entries[idx].location
        );
        registry.entries[idx].why = reason.to_string();
        registry
            .save(&config_path)
            .context("Failed to save registry")?;

        let next_idx = registry
            .entries
            .iter()
            .position(|e| e.why.trim().is_empty());

        if let Some(next) = next_idx {
            let remaining = registry
                .entries
                .iter()
                .filter(|e| e.why.trim().is_empty())
                .count();
            println!("{} remaining.\n", remaining);
            print_entry_snippet(&registry.entries[next], registry_dir);
            println!(
                "\nFix with:\n  shame next \"<reason>\"\n  shame fix \"{}\" \"{}\" --why \"<reason>\"",
                registry.entries[next].location, registry.entries[next].token
            );
        } else {
            print_remaining(0);
        }
    } else {
        print_entry_snippet(&registry.entries[idx], registry_dir);
        println!(
            "\nFix with:\n  shame next \"<reason>\"\n  shame fix \"{}\" \"{}\" --why \"<reason>\"",
            registry.entries[idx].location, registry.entries[idx].token
        );
        let remaining = registry
            .entries
            .iter()
            .filter(|e| e.why.trim().is_empty())
            .count();
        if remaining > 1 {
            println!("{} more entries need documentation.", remaining - 1);
        }
    }

    Ok(())
}

fn handle_remove(location: &str, token: &str) -> Result<()> {
    let config_path = find_registry_path()?;
    let mut registry = Registry::load(&config_path).context("Failed to load registry")?;

    let entry_idx = registry
        .entries
        .iter()
        .position(|e| e.location == location && e.token == token)
        .ok_or_else(|| anyhow::anyhow!("No entry found for {} with token '{}'", location, token))?;

    let removed = registry.entries.remove(entry_idx);

    println!("Removed: {} at {}", removed.token, removed.location);

    registry
        .save(&config_path)
        .context("Failed to save registry")?;

    let remaining = registry
        .entries
        .iter()
        .filter(|e| e.why.trim().is_empty())
        .count();
    print_remaining(remaining);

    Ok(())
}

fn handle_fix(location: &str, token: &str, why: &str) -> Result<()> {
    if why.trim().is_empty() {
        eprintln!("Error: --why cannot be empty or whitespace-only.");
        std::process::exit(1);
    }

    let config_path = find_registry_path()?;
    let mut registry = Registry::load(&config_path).context("Failed to load registry")?;

    let entry_idx = registry
        .entries
        .iter()
        .position(|e| e.location == location && e.token == token)
        .ok_or_else(|| anyhow::anyhow!("No entry found for {} with token '{}'", location, token))?;

    registry.entries[entry_idx].why = why.to_string();

    println!(
        "Documented: {} at {}",
        registry.entries[entry_idx].token, registry.entries[entry_idx].location
    );

    registry
        .save(&config_path)
        .context("Failed to save registry")?;

    let remaining = registry
        .entries
        .iter()
        .filter(|e| e.why.trim().is_empty())
        .count();
    print_remaining(remaining);

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;
    use std::collections::HashMap;

    fn entry(location: &str, token: &str, content: &str) -> Entry {
        Entry {
            location: location.to_string(),
            token: token.to_string(),
            content: content.to_string(),
            created_at: Utc.with_ymd_and_hms(2024, 1, 1, 0, 0, 0).unwrap(),
            owner: "alice".to_string(),
            why: "because".to_string(),
        }
    }

    fn violation(path: &str, line: u32, content: &str, token: &str) -> scanner::Violation {
        scanner::Violation {
            path: PathBuf::from(path),
            line_number: line,
            line_content: content.to_string(),
            matched_token: token.to_string(),
        }
    }

    #[test]
    fn cascade_match_exact_location_pairs_each_violation_with_its_entry() {
        let entries = vec![
            entry("./a.py:10", "# noqa", "x = 1  # noqa"),
            entry("./b.py:20", "# noqa", "y = 2  # noqa"),
        ];
        let violations = vec![
            violation("./a.py", 10, "x = 1  # noqa", "# noqa"),
            violation("./b.py", 20, "y = 2  # noqa", "# noqa"),
        ];
        let m = cascade_match(&entries, &violations, &HashMap::new());
        assert_eq!(m.violation_to_entry, vec![Some(0), Some(1)]);
        assert_eq!(m.entry_to_violation, vec![Some(0), Some(1)]);
    }

    #[test]
    fn cascade_match_uses_content_hash_when_line_shifted() {
        // Entry was at line 10, now the same content is at line 12 (line shift after edit).
        let entries = vec![entry("./a.py:10", "# noqa", "x = 1  # noqa")];
        let violations = vec![violation("./a.py", 12, "x = 1  # noqa", "# noqa")];
        let m = cascade_match(&entries, &violations, &HashMap::new());
        assert_eq!(m.violation_to_entry, vec![Some(0)]);
    }

    #[test]
    fn cascade_match_follows_renames() {
        // Entry references old.py but the file was renamed to new.py; content unchanged.
        let entries = vec![entry("./old.py:10", "# noqa", "x = 1  # noqa")];
        let violations = vec![violation("./new.py", 10, "x = 1  # noqa", "# noqa")];
        let mut renames = HashMap::new();
        renames.insert("./old.py".to_string(), "./new.py".to_string());
        let m = cascade_match(&entries, &violations, &renames);
        assert_eq!(m.violation_to_entry, vec![Some(0)]);
    }

    #[test]
    fn cascade_match_unmatched_violation_has_none() {
        let entries: Vec<Entry> = vec![];
        let violations = vec![violation("./a.py", 1, "x = 1  # noqa", "# noqa")];
        let m = cascade_match(&entries, &violations, &HashMap::new());
        assert_eq!(m.violation_to_entry, vec![None]);
    }

    #[test]
    fn cascade_match_does_not_pair_different_tokens_at_same_location() {
        let entries = vec![entry(
            "./a.py:10",
            "# noqa",
            "x = 1  # noqa  # type: ignore",
        )];
        let violations = vec![violation(
            "./a.py",
            10,
            "x = 1  # noqa  # type: ignore",
            "# type: ignore",
        )];
        let m = cascade_match(&entries, &violations, &HashMap::new());
        assert_eq!(m.violation_to_entry, vec![None]);
        assert_eq!(m.entry_to_violation, vec![None]);
    }

    #[test]
    fn is_entry_in_scope_true_when_file_was_scanned() {
        let entry = entry("./src/foo.py:1", "# noqa", "");
        let mut scanned = HashSet::new();
        scanned.insert(PathBuf::from("./src/foo.py"));
        let registry_dir = PathBuf::from("/repo");
        assert!(is_entry_in_scope(
            &entry,
            &scanned,
            &HashSet::new(),
            &[],
            &registry_dir,
        ));
    }

    #[test]
    fn is_entry_in_scope_false_when_file_was_skipped() {
        let entry = entry("./src/foo.py:1", "# noqa", "");
        let mut skipped = HashSet::new();
        skipped.insert(PathBuf::from("./src/foo.py"));
        let registry_dir = PathBuf::from("/repo");
        assert!(!is_entry_in_scope(
            &entry,
            &HashSet::new(),
            &skipped,
            &[],
            &registry_dir,
        ));
    }

    #[test]
    fn is_entry_in_scope_falls_back_to_path_prefix() {
        let entry = entry("./src/foo.py:1", "# noqa", "");
        let scan_paths = vec![PathBuf::from("./src")];
        let registry_dir = PathBuf::from("/repo");
        assert!(is_entry_in_scope(
            &entry,
            &HashSet::new(),
            &HashSet::new(),
            &scan_paths,
            &registry_dir,
        ));
    }

    #[cfg(windows)]
    #[test]
    fn is_entry_in_scope_normalizes_windows_verbatim_registry_prefix() {
        let entry = entry(r"C:\repo\src\deleted.py:1", "# noqa", "");
        let scan_paths = vec![PathBuf::from("src")];
        let registry_dir = PathBuf::from(r"\\?\C:\repo");
        assert!(is_entry_in_scope(
            &entry,
            &HashSet::new(),
            &HashSet::new(),
            &scan_paths,
            &registry_dir,
        ));
    }

    #[test]
    fn is_entry_in_scope_false_when_outside_scan_paths() {
        let entry = entry("./other/foo.py:1", "# noqa", "");
        let scan_paths = vec![PathBuf::from("./src")];
        let registry_dir = PathBuf::from("/repo");
        assert!(!is_entry_in_scope(
            &entry,
            &HashSet::new(),
            &HashSet::new(),
            &scan_paths,
            &registry_dir,
        ));
    }

    #[cfg(not(windows))]
    #[test]
    fn is_entry_in_scope_false_when_absolute_entry_outside_registry() {
        // Absolute entry whose path is not under the registry directory.
        // strip_registry_prefix's first attempt fails and the non-Windows
        // fallback returns None, so the entry stays absolute and matches
        // neither scanned_files nor any scan_path prefix.
        let entry = entry("/elsewhere/foo.py:1", "# noqa", "");
        let scan_paths = vec![PathBuf::from("src")];
        let registry_dir = PathBuf::from("/repo");
        assert!(!is_entry_in_scope(
            &entry,
            &HashSet::new(),
            &HashSet::new(),
            &scan_paths,
            &registry_dir,
        ));
    }
}
