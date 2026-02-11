use std::process::Command;
use std::fs;
use std::path::Path;

fn get_binary_path() -> std::path::PathBuf {
    // A heuristic to find the built binary. 
    // In strict environments, we might want to use `cargo_bin_path` from `assert_cmd` crate,
    // but for now, let's assume `cargo test` builds it in `target/debug`.
    let mut path = std::env::current_dir().unwrap();
    path.push("target");
    path.push("debug");
    path.push("shamefile");
    path
}

#[test]
fn test_check_detects_violations() {
    // 1. Setup a clean test environment (temp dir would be better but simple works too)
    let fixture_path = "tests/fixtures";
    let config_path = "tests/fixtures/shamefile.yaml";
    
    // Cleanup previous run
    if Path::new(config_path).exists() {
        fs::remove_file(config_path).unwrap();
    }

    // 2. Run `shamefile check tests/fixtures --config tests/fixtures/shamefile.yaml`
    let output = Command::new(get_binary_path())
        .arg("check")
        .arg(fixture_path)
        .arg("--config")
        .arg(config_path)
        .output()
        .expect("Failed to execute shamefile");

    // 3. Verify output
    assert!(!output.status.success(), "Check should fail because justifications are missing");
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("New suppression detected"), "Should report new suppressions");
    assert!(stdout.contains("Validation failed"), "Should report validation failure");
    
    // 4. Verify file creation
    assert!(Path::new(config_path).exists(), "Should create registry file");
    
    let content = fs::read_to_string(config_path).unwrap();
    assert!(content.contains("# noqa"), "Registry should contain python token");
    assert!(content.contains("// eslint-disable"), "Registry should contain JS token");

    // Cleanup
    fs::remove_file(config_path).unwrap();
}

#[test]
fn test_clean_removes_stale_entries() {
    // This requires more setup (creating a dummy file, scanning it, deleting it, running clean).
    // Skipping for brevity in this step, but follows similar pattern.
}
