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
        /// Path to scan (file or directory)
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
    let config_path = scan_path.join("shamefile.yaml");

    if dry_run {
        handle_dry_run(scan_path, &config_path)
    } else {
        handle_normal(scan_path, &config_path)
    }
}

fn handle_normal(scan_path: &Path, config_path: &Path) -> Result<()> {
    // 1. Load or create registry
    let mut registry = if config_path.exists() {
        Registry::load(config_path).context("Failed to load registry")?
    } else {
        println!("Creating new registry at {}", config_path.display());
        Registry::new()
    };

    // 2. Scan for violations (exclude shamefile.yaml itself)
    println!("Scanning {} for suppressions...", scan_path.display());
    let all_violations = scanner::scan(scan_path).context("Failed to scan files")?;
    let violations: Vec<_> = all_violations
        .into_iter()
        .filter(|v| v.path != config_path)
        .collect();
    println!("Found {} suppressions in code.", violations.len());

    let mut new_entries_count = 0;
    let mut errors_found = false;

    // 3. Add new suppressions to registry
    for violation in &violations {
        let violation_path_str = violation.path.to_string_lossy().to_string();

        let existing = registry.entries.iter().find(|e| {
            e.file == violation_path_str
                && e.line == violation.line_number
                && e.token == violation.matched_token
        });

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
                file: violation_path_str,
                line: violation.line_number,
                token: violation.matched_token.clone(),
                author: shamefile::git::get_git_author(),
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
            v.path.to_string_lossy() == entry.file
                && v.line_number == entry.line
                && v.matched_token == entry.token
        });
        if !is_valid {
            println!(
                "Removing stale entry: {} at {}:{}",
                entry.token, entry.file, entry.line
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
                "Missing reason (why): {} at {}:{}",
                entry.token, entry.file, entry.line
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

    // 7. Exit 1 if errors
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

fn handle_dry_run(scan_path: &Path, config_path: &Path) -> Result<()> {
    // 1. Load existing registry (fail if missing)
    if !config_path.exists() {
        eprintln!(
            "Registry not found at {}. Run `shame me` first to create it.",
            config_path.display()
        );
        std::process::exit(1);
    }
    let registry = Registry::load(config_path).context("Failed to load registry")?;

    // 2. Scan for violations (exclude shamefile.yaml itself)
    println!(
        "Step 1: Scanning {} for suppressions...",
        scan_path.display()
    );
    let all_violations = scanner::scan(scan_path).context("Failed to scan files")?;
    let violations: Vec<_> = all_violations
        .into_iter()
        .filter(|v| v.path != config_path)
        .collect();
    println!("Found {} suppressions in code.", violations.len());

    let mut failed = false;

    // Step 2: Coverage check (code ⊆ registry)
    println!("\nStep 2: Checking coverage (code -> shamefile)...");
    let undocumented: Vec<_> = violations
        .iter()
        .filter(|v| {
            let vpath = v.path.to_string_lossy();
            !registry.entries.iter().any(|e| {
                e.file == vpath.as_ref() && e.line == v.line_number && e.token == v.matched_token
            })
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
                v.path.to_string_lossy() == e.file
                    && v.line_number == e.line
                    && v.matched_token == e.token
            })
        })
        .collect();

    if stale.is_empty() {
        println!("OK: No stale entries.");
    } else {
        println!("FAIL: Found {} stale entries:", stale.len());
        for e in &stale {
            println!(
                "  - {} at {}:{} (not in code anymore)",
                e.token, e.file, e.line
            );
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
            println!("  - {} at {}:{}", e.token, e.file, e.line);
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
