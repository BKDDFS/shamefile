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

fn cascade_match(old_entries: &[Entry], violations: &[scanner::Violation]) -> MatchResult {
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
    for (vi, v) in violations.iter().enumerate() {
        if v2e[vi].is_some() {
            continue;
        }
        let v_file = v.path.to_string_lossy();
        let v_hash = content_hash(&v.line_content);
        if let Some(oi) = old_entries.iter().enumerate().find_map(|(i, e)| {
            if e2v[i].is_none()
                && e.file() == v_file.as_ref()
                && e.shame_vector == v_hash
                && e.token == v.matched_token
            {
                Some(i)
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
        entry_file_raw
            .strip_prefix(registry_dir_canonical)
            .map(|p| p.to_path_buf())
            .unwrap_or(entry_file_raw)
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

struct NormalizedScanData {
    violations: Vec<scanner::Violation>,
    scanned_files: HashSet<PathBuf>,
    skipped_files: HashSet<PathBuf>,
}

/// Filters out shamefile.yaml from violations and normalizes paths relative to registry_dir.
fn filter_and_normalize(
    violations: Vec<scanner::Violation>,
    scanned_files: HashSet<PathBuf>,
    skipped_files: HashSet<PathBuf>,
    config_path: &Path,
    registry_dir: &Path,
) -> Result<NormalizedScanData> {
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

    let normalize_paths = |files: HashSet<PathBuf>| -> HashSet<PathBuf> {
        files
            .into_iter()
            .filter_map(|f| {
                let f_canonical = std::fs::canonicalize(&f).ok()?;
                if let Ok(relative) = f_canonical.strip_prefix(&registry_dir_canonical) {
                    Some(relative.to_path_buf())
                } else {
                    Some(f)
                }
            })
            .collect()
    };

    Ok(NormalizedScanData {
        violations: normalized_violations,
        scanned_files: normalize_paths(scanned_files),
        skipped_files: normalize_paths(skipped_files),
    })
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
        config_path,
        registry_dir,
    )?;
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

    // 3. Cascade matching: reconcile violations with existing entries
    let matches = cascade_match(&registry.entries, &violations);
    let old_entries = std::mem::take(&mut registry.entries);

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

    let mut new_entries_count = 0;
    let mut removed_count = 0;
    let mut errors_found = false;

    // 3a. Build entries from matched violations (preserve metadata, update location/shame_vector)
    for (vi, v) in violations.iter().enumerate() {
        let v_path_str = v.path.to_string_lossy().to_string();
        let new_location = Entry::make_location(&v_path_str, v.line_number);
        let new_sv = content_hash(&v.line_content);

        if let Some(oi) = matches.violation_to_entry[vi] {
            let old = &old_entries[oi];
            registry.entries.push(Entry {
                location: new_location,
                token: v.matched_token.clone(),
                shame_vector: new_sv,
                owner: old.owner.clone(),
                created_at: old.created_at,
                why: old.why.clone(),
            });
        } else {
            // New entry — no match in old registry
            println!(
                "New suppression detected: {} at {}:{}",
                v.matched_token, v_path_str, v.line_number
            );
            registry.entries.push(Entry {
                location: new_location,
                token: v.matched_token.clone(),
                shame_vector: new_sv,
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
            &registry_dir_canonical,
        );
        let entry_file_raw = PathBuf::from(old.file());
        let entry_file_normalized = if entry_file_raw.is_absolute() {
            entry_file_raw
                .strip_prefix(&registry_dir_canonical)
                .map(|p| p.to_path_buf())
                .unwrap_or(entry_file_raw)
        } else {
            entry_file_raw
        };
        if !in_scope {
            // Out of scan scope — preserve unchanged
            registry.entries.push(old.clone());
        } else if scanned_files.contains(&entry_file_normalized) {
            // File was scanned. Check if any violation in this file has the same token
            // (but didn't match by location or content hash).
            let has_token_in_file = violations
                .iter()
                .any(|v| v.path == entry_file_normalized && v.matched_token == old.token);
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
        println!("Unmatched stale entries (algorithmic matching failed):");
        for e in &unmatched_stale {
            println!(
                "  - {} at {} (line changed or removed)",
                e.token, e.location
            );
        }
        // Keep them in registry — user must resolve manually
        registry.entries.extend(unmatched_stale);
        errors_found = true;
    }

    // 4. Validate justifications
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

    // 5. Save registry
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

    // 6. Exit 1 if registry changed or errors
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
        config_path,
        registry_dir,
    )?;
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
    let matches = cascade_match(&registry.entries, &violations);

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
                &registry_dir_canonical,
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
