use std::fs;
use std::process::Command;

fn get_binary_path() -> std::path::PathBuf {
    let mut path = std::env::current_dir().unwrap();
    path.push("target");
    path.push("debug");
    path.push("shame");
    path
}

/// Create a temp dir with copies of fixture files for isolated testing.
fn setup_temp_fixtures() -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    fs::copy("tests/fixtures/sample.py", tmp.path().join("sample.py")).unwrap();
    fs::copy("tests/fixtures/sample.js", tmp.path().join("sample.js")).unwrap();
    tmp
}

#[test]
fn test_me_detects_new_suppressions() {
    let tmp = setup_temp_fixtures();
    let dir = tmp.path();
    let config_path = dir.join("shamefile.yaml");

    let output = Command::new(get_binary_path())
        .arg("me")
        .arg(dir)
        .output()
        .expect("Failed to execute shame");

    // Should fail because justifications are missing
    assert!(
        !output.status.success(),
        "Should fail because justifications are missing"
    );
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(
        stdout.contains("New suppression detected"),
        "Should report new suppressions: {stdout}"
    );
    assert!(
        stdout.contains("Validation failed"),
        "Should report validation failure: {stdout}"
    );

    // Should create registry file
    assert!(config_path.exists(), "Should create registry file");

    let content = fs::read_to_string(&config_path).unwrap();
    assert!(
        content.contains("# noqa"),
        "Registry should contain python token"
    );
    assert!(
        content.contains("// eslint-disable"),
        "Registry should contain JS token"
    );
}

#[test]
fn test_dry_run_fails_without_registry() {
    let tmp = setup_temp_fixtures();
    let dir = tmp.path();

    let output = Command::new(get_binary_path())
        .arg("me")
        .arg(dir)
        .arg("--dry-run")
        .output()
        .expect("Failed to execute shame");

    assert!(
        !output.status.success(),
        "Dry-run should fail when no registry exists"
    );
    let stderr = String::from_utf8(output.stderr).unwrap();
    assert!(
        stderr.contains("Registry not found"),
        "Should report missing registry: {stderr}"
    );
}

#[test]
fn test_dry_run_validates_existing_registry() {
    let tmp = setup_temp_fixtures();
    let dir = tmp.path();

    // Create registry via normal mode first
    Command::new(get_binary_path())
        .arg("me")
        .arg(dir)
        .output()
        .expect("Failed to execute shame");

    // Now dry-run should fail (entries have no justifications)
    let output = Command::new(get_binary_path())
        .arg("me")
        .arg(dir)
        .arg("--dry-run")
        .output()
        .expect("Failed to execute shame");

    assert!(
        !output.status.success(),
        "Dry-run should fail with missing justifications"
    );
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(
        stdout.contains("without reason"),
        "Should report missing reasons: {stdout}"
    );
}

#[test]
fn test_short_flag_n_for_dry_run() {
    let tmp = setup_temp_fixtures();
    let dir = tmp.path();

    // -n without registry should fail the same as --dry-run
    let output = Command::new(get_binary_path())
        .arg("me")
        .arg(dir)
        .arg("-n")
        .output()
        .expect("Failed to execute shame");

    assert!(
        !output.status.success(),
        "-n should fail when no registry exists"
    );
    let stderr = String::from_utf8(output.stderr).unwrap();
    assert!(
        stderr.contains("Registry not found"),
        "-n should behave like --dry-run: {stderr}"
    );
}
