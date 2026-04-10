use anyhow::{Context, Result};
use chrono::Utc;
use clap::{Parser, Subcommand};
use shamefile::registry::{Entry, Registry};
use shamefile::scanner;
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
        /// Directory to scan
        #[arg(default_value = ".")]
        path: PathBuf,

        /// Read-only validation for CI/CD (never saves)
        #[arg(short = 'n', long)]
        dry_run: bool,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Me { path, dry_run } => {
            handle_me(&path, dry_run)?;
        }
    }
    Ok(())
}

fn handle_me(scan_path: &Path, dry_run: bool) -> Result<()> {
    // 1. Validate that path exists (file or directory)
    if !scan_path.exists() {
        eprintln!("Error: path does not exist: {}", scan_path.display());
        std::process::exit(1);
    }

    // 2. Determine registry location: git root or CWD
    let cwd = std::env::current_dir().context("Failed to get current directory")?;
    let registry_dir = shamefile::git::find_git_root(&cwd).unwrap_or_else(|| cwd.clone());
    let config_path = registry_dir.join("shamefile.yaml");

    // 3. Dispatch
    if dry_run {
        handle_dry_run(scan_path, &config_path, &registry_dir)
    } else {
        handle_normal(scan_path, &config_path, &registry_dir)
    }
}

fn handle_normal(scan_path: &Path, config_path: &Path, registry_dir: &Path) -> Result<()> {
    // 1. Load or create registry
    let is_first_run = !config_path.exists();
    let mut registry = if is_first_run {
        println!("Creating new registry at {}", config_path.display());
        Registry::new()
    } else {
        Registry::load(config_path).context("Failed to load registry")?
    };

    // 2. Scan for violations
    println!("Scanning {} for suppressions...", scan_path.display());
    let all_violations = scanner::scan(scan_path).context("Failed to scan files")?;

    // 2a. Rebase violations to be relative to registry_dir and filter shamefile.yaml
    let registry_dir_canonical = std::fs::canonicalize(registry_dir)
        .context("Failed to canonicalize registry directory")?;
    let config_path_canonical = std::fs::canonicalize(config_path)
        .unwrap_or_else(|_| config_path.to_path_buf());

    let mut violations: Vec<_> = all_violations
        .into_iter()
        .filter_map(|mut v| {
            // Skip shamefile.yaml itself
            if let Ok(v_canonical) = std::fs::canonicalize(&v.path) {
                if v_canonical == config_path_canonical {
                    return None;
                }
            }

            // Rebase path to be relative to registry_dir
            if let Ok(v_absolute) = std::fs::canonicalize(&v.path) {
                if let Ok(relative) = v_absolute.strip_prefix(&registry_dir_canonical) {
                    v.path = relative.to_path_buf();
                }
            }

            Some(v)
        })
        .collect();

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
                        scan_path,
                    )
                    .unwrap_or_else(|| shamefile::git::get_git_current_user(scan_path))
                } else {
                    shamefile::git::get_git_current_user(scan_path)
                },
                created_at: Utc::now(),
                why: String::new(),
            });
            new_entries_count += 1;
            errors_found = true;
        }
    }

    // 4. Remove stale entries
    let initial_count = registry.entries.len();
    registry.entries.retain(|entry| {
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

fn handle_dry_run(scan_path: &Path, config_path: &Path, registry_dir: &Path) -> Result<()> {
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
    println!(
        "Step 1: Scanning {} for suppressions...",
        scan_path.display()
    );
    let all_violations = scanner::scan(scan_path).context("Failed to scan files")?;

    // 2a. Rebase violations to be relative to registry_dir and filter shamefile.yaml
    let registry_dir_canonical = std::fs::canonicalize(registry_dir)
        .context("Failed to canonicalize registry directory")?;
    let config_path_canonical = std::fs::canonicalize(config_path)
        .unwrap_or_else(|_| config_path.to_path_buf());

    let violations: Vec<_> = all_violations
        .into_iter()
        .filter_map(|mut v| {
            // Skip shamefile.yaml itself
            if let Ok(v_canonical) = std::fs::canonicalize(&v.path) {
                if v_canonical == config_path_canonical {
                    return None;
                }
            }

            // Rebase path to be relative to registry_dir
            if let Ok(v_absolute) = std::fs::canonicalize(&v.path) {
                if let Ok(relative) = v_absolute.strip_prefix(&registry_dir_canonical) {
                    v.path = relative.to_path_buf();
                }
            }

            Some(v)
        })
        .collect();

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

    // Step 3: Stale check (registry ⊆ code)
    println!("\nStep 3: Checking for stale entries (shamefile -> code)...");
    let stale: Vec<_> = registry
        .entries
        .iter()
        .filter(|e| {
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
