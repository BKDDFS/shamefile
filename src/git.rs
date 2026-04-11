use std::path::{Path, PathBuf};
use std::process::Command;

/// Find the git repository root using `git rev-parse --show-toplevel`.
/// Returns None if not inside a git repository.
pub fn find_git_root(start: &Path) -> Option<PathBuf> {
    let output = Command::new("git")
        .arg("rev-parse")
        .arg("--show-toplevel")
        .current_dir(start)
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if path.is_empty() {
        None
    } else {
        Some(PathBuf::from(path))
    }
}

/// Fetch the current git user and email for a given repo path.
/// Returns "Name <email>" or "Unknown" if git is not configured.
pub fn get_git_current_user(repo_path: &Path) -> String {
    let name = get_git_config("user.name", repo_path).unwrap_or_else(|| "Unknown".to_string());
    let email = get_git_config("user.email", repo_path)
        .unwrap_or_else(|| "unknown@example.com".to_string());

    if name == "Unknown" && email == "unknown@example.com" {
        return "Unknown".to_string();
    }

    format!("{} <{}>", name, email)
}

/// Fetch the author of a specific line using git blame.
/// Returns "Name <email>" or None if blame fails.
pub fn get_git_blame_author(file: &str, line: u32, repo_path: &Path) -> Option<String> {
    let output = Command::new("git")
        .args([
            "blame",
            "-L",
            &format!("{},{}", line, line),
            "--porcelain",
            file,
        ])
        .current_dir(repo_path)
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let text = String::from_utf8_lossy(&output.stdout);
    let mut name = None;
    let mut email = None;

    for line in text.lines() {
        if let Some(val) = line.strip_prefix("author ") {
            name = Some(val.to_string());
        }
        if let Some(val) = line.strip_prefix("author-mail ") {
            email = Some(val.trim_matches(|c| c == '<' || c == '>').to_string());
        }
    }

    match (name, email) {
        (Some(n), Some(e)) => Some(format!("{} <{}>", n, e)),
        _ => None,
    }
}

fn get_git_config(key: &str, repo_path: &Path) -> Option<String> {
    let output = Command::new("git")
        .arg("config")
        .arg("--get")
        .arg(key)
        .current_dir(repo_path)
        .output()
        .ok()?;

    if output.status.success() {
        let val = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if val.is_empty() { None } else { Some(val) }
    } else {
        None
    }
}
