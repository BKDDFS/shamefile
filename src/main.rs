use anyhow::{Context, Result};
use chrono::Utc;
use clap::{Parser, Subcommand};
use shamefile::registry::{Entry, Registry};
use shamefile::scanner;
use std::collections::HashSet;
use std::path::{Path, PathBuf};

#[derive(Parser)]
#[command(name = "shame")]
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
        handle_dry_run(scan_paths, &config_path, &registry_dir, hidden)
    } else {
        handle_normal(scan_paths, &config_path, &registry_dir, hidden)
    }
}

/// Filters out shamefile.yaml from violations and normalizes paths relative to registry_dir.
/// Also normalizes scanned_files paths the same way.
fn filter_and_normalize(
    violations: Vec<scanner::Violation>,
    scanned_files: HashSet<PathBuf>,
    config_path: &Path,
    registry_dir: &Path,
) -> Result<(Vec<scanner::Violation>, HashSet<PathBuf>)> {
    let registry_dir_canonical =
        std::fs::canonicalize(registry_dir).context("Failed to canonicalize registry directory")?;
    let config_path_canonical =
        std::fs::canonicalize(config_path).unwrap_or_else(|_| config_path.to_path_buf());

    let normalized_violations = violations
        .into_iter()
        .filter_map(|mut v| {
            let v_canonical = std::fs::canonicalize(&v.path).ok()?;

            if v_canonical == config_path_canonical {
                return None;
            }

            if let Ok(relative) = v_canonical.strip_prefix(&registry_dir_canonical) {
                v.path = relative.to_path_buf();
            }

            Some(v)
        })
        .collect();

    let normalized_files = scanned_files
        .into_iter()
        .filter_map(|f| {
            let f_canonical = std::fs::canonicalize(&f).ok()?;
            if let Ok(relative) = f_canonical.strip_prefix(&registry_dir_canonical) {
                Some(relative.to_path_buf())
            } else {
                Some(f)
            }
        })
        .collect();

    Ok((normalized_violations, normalized_files))
}

fn handle_normal(
    scan_paths: &[PathBuf],
    config_path: &Path,
    registry_dir: &Path,
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
    for path in scan_paths {
        println!("Scanning {} for suppressions...", path.display());
        let result = scanner::scan(path, hidden).context("Failed to scan files")?;
        all_violations.extend(result.violations);
        all_scanned_files.extend(result.scanned_files);
    }
    let (mut violations, scanned_files) =
        filter_and_normalize(all_violations, all_scanned_files, config_path, registry_dir)?;
    violations.sort_by(|a, b| {
        (&a.path, a.line_number, &a.matched_token).cmp(&(&b.path, b.line_number, &b.matched_token))
    });
    violations.dedup_by(|a, b| {
        a.path == b.path && a.line_number == b.line_number && a.matched_token == b.matched_token
    });

    println!("Found {} suppressions in code.", violations.len());

    let mut new_entries_count = 0;
    let mut errors_found = false;

    // 3. Add new suppressions to registry
    for violation in &violations {
        let violation_path_str = violation.path.to_string_lossy().to_string();

        let violation_location = Entry::make_location(&violation_path_str, violation.line_number);

        let existing = registry
            .entries
            .iter()
            .find(|e| e.location == violation_location && e.token == violation.matched_token);

        if let Some(entry) = existing {
            if entry.why.trim().is_empty() {
                errors_found = true;
            }
        } else {
            println!(
                "New suppression detected: {} at {}:{}",
                violation.matched_token, violation_path_str, violation.line_number
            );
            registry.entries.push(Entry {
                location: violation_location,
                token: violation.matched_token.clone(),
                owner: if is_first_run {
                    shamefile::git::get_git_blame_author(
                        &violation_path_str,
                        violation.line_number,
                        registry_dir,
                    )
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

    // 4. Remove stale entries (only if file is within scanned scope)
    //    A file is "in scope" if it was visited by the scanner OR if it falls
    //    under any of the scan paths (covers deleted/gitignored files).
    let registry_dir_canonical =
        std::fs::canonicalize(registry_dir).unwrap_or_else(|_| registry_dir.to_path_buf());
    let scan_paths_canonical: Vec<PathBuf> = scan_paths
        .iter()
        .filter_map(|p| std::fs::canonicalize(p).ok())
        .map(|c| {
            c.strip_prefix(&registry_dir_canonical)
                .map(|r| r.to_path_buf())
                .unwrap_or(c)
        })
        .collect();
    let initial_count = registry.entries.len();
    registry.entries.retain(|entry| {
        let entry_file_raw = PathBuf::from(entry.file());
        let entry_file = if entry_file_raw.is_absolute() {
            entry_file_raw
                .strip_prefix(&registry_dir_canonical)
                .map(|p| p.to_path_buf())
                .unwrap_or(entry_file_raw)
        } else {
            entry_file_raw
        };
        let in_scope = scanned_files.contains(&entry_file)
            || scan_paths_canonical
                .iter()
                .any(|sp| entry_file.starts_with(sp));
        if !in_scope {
            return true; // not in scan scope — leave it alone
        }
        let is_valid = violations.iter().any(|v| {
            let loc = Entry::make_location(&v.path.to_string_lossy(), v.line_number);
            loc == entry.location && v.matched_token == entry.token
        });
        if !is_valid {
            println!(
                "Removing stale entry: {} at {}",
                entry.token, entry.location
            );
        }
        is_valid
    });
    let removed_count = initial_count - registry.entries.len();

    // 5. Validate justifications
    let missing_why: Vec<_> = registry
        .entries
        .iter()
        .filter(|e| e.why.trim().is_empty())
        .collect();

    if !missing_why.is_empty() {
        for entry in &missing_why {
            println!(
                "Missing reason (why): {} at {}",
                entry.token, entry.location
            );
        }
        errors_found = true;
    }

    // 6. Save registry
    registry
        .save(config_path)
        .context("Failed to save registry")?;
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
    }

    // 7. Exit 1 if registry changed or errors
    if removed_count > 0 {
        errors_found = true;
    }
    if errors_found {
        println!(
            "Validation failed! Please add reasons (why) to {}",
            config_path.display()
        );
        std::process::exit(1);
    }

    println!("Validation passed. No shame today!");

    Ok(())
}

fn handle_dry_run(
    scan_paths: &[PathBuf],
    config_path: &Path,
    registry_dir: &Path,
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
    for path in scan_paths {
        println!("Step 1: Scanning {} for suppressions...", path.display());
        let result = scanner::scan(path, hidden).context("Failed to scan files")?;
        all_violations.extend(result.violations);
        all_scanned_files.extend(result.scanned_files);
    }
    let (mut violations, scanned_files) =
        filter_and_normalize(all_violations, all_scanned_files, config_path, registry_dir)?;
    violations.sort_by(|a, b| {
        (&a.path, a.line_number, &a.matched_token).cmp(&(&b.path, b.line_number, &b.matched_token))
    });
    violations.dedup_by(|a, b| {
        a.path == b.path && a.line_number == b.line_number && a.matched_token == b.matched_token
    });

    println!("Found {} suppressions in code.", violations.len());

    let mut failed = false;

    // Step 2: Coverage check (code ⊆ registry)
    println!("\nStep 2: Checking coverage (code -> shamefile)...");
    let undocumented: Vec<_> = violations
        .iter()
        .filter(|v| {
            let loc = Entry::make_location(&v.path.to_string_lossy(), v.line_number);
            !registry
                .entries
                .iter()
                .any(|e| e.location == loc && e.token == v.matched_token)
        })
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
    let registry_dir_canonical =
        std::fs::canonicalize(registry_dir).unwrap_or_else(|_| registry_dir.to_path_buf());
    let scan_paths_canonical: Vec<PathBuf> = scan_paths
        .iter()
        .filter_map(|p| std::fs::canonicalize(p).ok())
        .map(|c| {
            c.strip_prefix(&registry_dir_canonical)
                .map(|r| r.to_path_buf())
                .unwrap_or(c)
        })
        .collect();
    let stale: Vec<_> = registry
        .entries
        .iter()
        .filter(|e| {
            let entry_file_raw = PathBuf::from(e.file());
            let entry_file = if entry_file_raw.is_absolute() {
                entry_file_raw
                    .strip_prefix(&registry_dir_canonical)
                    .map(|p| p.to_path_buf())
                    .unwrap_or(entry_file_raw)
            } else {
                entry_file_raw
            };
            let in_scope = scanned_files.contains(&entry_file)
                || scan_paths_canonical
                    .iter()
                    .any(|sp| entry_file.starts_with(sp));
            if !in_scope {
                return false; // not in scan scope — not stale
            }
            !violations.iter().any(|v| {
                let loc = Entry::make_location(&v.path.to_string_lossy(), v.line_number);
                loc == e.location && v.matched_token == e.token
            })
        })
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
