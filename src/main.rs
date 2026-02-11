use anyhow::{Context, Result};
use chrono::Utc;
use clap::{Parser, Subcommand};
use shamefile::registry::{Entry, Registry};
use shamefile::{scanner, ShamefileError, gamify};
use std::path::{Path, PathBuf};

#[derive(Parser)]
#[command(name = "shame")]
#[command(about = "A tool to enforce documentation for code suppressions", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Path to the configuration/registry file
    #[arg(long, default_value = "shamefile.yaml")]
    config: PathBuf,
}

#[derive(Subcommand)]
enum Commands {
    /// Check for undocumented suppressions and validate existing ones
    Check {
        /// Paths to scan (files or directories)
        #[arg(default_value = ".")]
        path: PathBuf,
    },
    /// Remove stale entries from the registry (clean up)
    Me {
        /// Paths to scan (files or directories)
        #[arg(default_value = ".")]
        path: PathBuf,

        /// Output without gamification or personality
        #[arg(long)]
        boring: bool,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let config_path = cli.config;

    match cli.command {
        Commands::Check { path } => {
            handle_check(&path, &config_path)?;
        }
        Commands::Me { path, boring } => {
            handle_clean(&path, &config_path, boring)?;
        }
    }
    Ok(())
}

fn handle_clean(scan_path: &Path, config_path: &Path, boring: bool) -> Result<()> {
    if !config_path.exists() {
        println!("Registry not found at {}", config_path.display());
        return Ok(());
    }

    println!("Scanning {} for stale suppressions...", scan_path.display());
    let mut registry = Registry::load(config_path).context("Failed to load registry")?;
    let violations = scanner::scan(scan_path).context("Failed to scan files")?;
    
    // Naive O(N*M) - iterate registry entries and check if they exist in violations
    // We match on (file, line, token)
    let initial_count = registry.entries.len();
    registry.entries.retain(|entry| {
        let is_valid = violations.iter().any(|v| 
            v.path.to_string_lossy() == entry.file && 
            v.line_number as usize == entry.line && 
            v.matched_token == entry.token
        );
        
        if !is_valid {
            println!("Removing stale entry: {} at {}:{}", entry.token, entry.file, entry.line);
        }
        is_valid
    });
    
    // Save changes first
    let removed_count = initial_count - registry.entries.len();
    if removed_count > 0 {
        registry.save(config_path).context("Failed to save registry")?;
        println!("Removed {} stale entries from {}", removed_count, config_path.display());
    } else {
        println!("No stale entries found.");
    }

    if !boring {
        // --- GAMIFICATION UI START ---
        let game_state = gamify::GameState::new(&registry);
        print_gamified_status(&game_state);
        // --- GAMIFICATION UI END ---
    } else {
        println!("Cleanup complete.");
    }

    Ok(())
}

fn print_gamified_status(state: &gamify::GameState) {
    println!("\n🎮 Code Health: {}/{} HP", state.current_hp, state.max_hp);
    
    // HP Bar
    let bar_width: usize = 20;
    let hp_percent = state.current_hp as f64 / state.max_hp as f64;
    let fill_width = (hp_percent * bar_width as f64).round() as usize;
    let empty_width = bar_width.saturating_sub(fill_width);
    let bar: String = "█".repeat(fill_width) + &"░".repeat(empty_width);
    println!("   {}", bar);

    // Constant Warning
    println!("\n☠️  WARNING: If HP hits 0, you will go to LEGACY HELL.");

    println!("");

    if state.is_legacy_hell {
        println!("╔═══════════════════════════════════════╗");
        println!("║     ☠️  You are in LEGACY HELL ☠️     ║");
        println!("╚═══════════════════════════════════════╝");
        std::process::exit(1);
    }
}

fn handle_check(scan_path: &Path, config_path: &Path) -> Result<()> {
    println!("Scanning {} for suppressions...", scan_path.display());
    
    // 1. Load or create registry
    let mut registry = if config_path.exists() {
        Registry::load(config_path).context("Failed to load registry")?
    } else {
        println!("Creating new registry at {}", config_path.display());
        Registry::new()
    };

    // 2. Scan for violations
    let violations = scanner::scan(scan_path).context("Failed to scan files")?;
    println!("Found {} suppressions in code.", violations.len());

    let mut new_entries_count = 0;
    let mut errors_found = false;

    // 3. Sync violations to registry
    // This is a naive O(N*M) sync for now, can be optimized later
    for violation in violations {
        // Normalize path to string for comparison
        let violation_path_str = violation.path.to_string_lossy().to_string();
        
        let existing = registry.entries.iter_mut().find(|e| 
            e.file == violation_path_str && 
            e.line == violation.line_number as usize && 
            e.token == violation.matched_token
        );

        if let Some(entry) = existing {
            // Entry exists, check justification
            if entry.justification.trim().is_empty() {
                println!("Error: Missing justification for {} at {}:{}", entry.token, entry.file, entry.line);
                errors_found = true;
            }
        } else {
            // New violation! Add to registry
            println!("New suppression detected: {} at {}:{}", violation.matched_token, violation_path_str, violation.line_number);
            registry.entries.push(Entry {
                file: violation_path_str,
                line: violation.line_number as usize,
                token: violation.matched_token,
                author: shamefile::git::get_git_author(),
                created_at: Utc::now(),
                justification: String::new(),
            });
            new_entries_count += 1;
            errors_found = true; // New entry means missing justification
        }
    }

    // 4. Save registry if changed
    if new_entries_count > 0 {
        registry.save(config_path).context("Failed to save registry")?;
        println!("Added {} new entries to {}", new_entries_count, config_path.display());
    }

    if errors_found {
        println!("Validation failed! Please add justifications to {}", config_path.display());
        std::process::exit(1);
    } else {
        println!("All suppressions are documented!");
        // Show lightweight gamification stats on check too?
        // Let's keep it clean for check, only show full UI on 'shame me'
    }

    Ok(())
}
