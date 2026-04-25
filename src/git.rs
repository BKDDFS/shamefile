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

    parse_git_root_stdout(&String::from_utf8_lossy(&output.stdout))
}

fn parse_git_root_stdout(stdout: &str) -> Option<PathBuf> {
    let path = stdout.trim();
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
        (Some(n), Some(e)) if n != "Not Committed Yet" => Some(format!("{} <{}>", n, e)),
        _ => None,
    }
}

/// Detect file renames in the last commit using `git diff HEAD~1..HEAD --name-status -M`.
/// Returns a map of old_path -> new_path for renamed files.
/// Returns empty map if git is unavailable or there are no commits.
pub fn detect_renames(registry_dir: &Path) -> std::collections::HashMap<String, String> {
    let output = Command::new("git")
        .args(["diff", "HEAD~1..HEAD", "--name-status", "-M"])
        .current_dir(registry_dir)
        .output();

    let output = match output {
        Ok(o) if o.status.success() => o,
        _ => return std::collections::HashMap::new(),
    };

    parse_renames(&String::from_utf8_lossy(&output.stdout))
}

fn parse_renames(text: &str) -> std::collections::HashMap<String, String> {
    let mut renames = std::collections::HashMap::new();
    for line in text.lines() {
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() == 3 && parts[0].starts_with('R') {
            let old = if parts[1].starts_with("./") {
                parts[1].to_string()
            } else {
                format!("./{}", parts[1])
            };
            let new = if parts[2].starts_with("./") {
                parts[2].to_string()
            } else {
                format!("./{}", parts[2])
            };
            renames.insert(old, new);
        }
    }
    renames
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_renames_handles_dot_slash_prefix() {
        let text = "R100\t./old.py\t./new.py\n";
        let map = parse_renames(text);
        assert_eq!(map.get("./old.py"), Some(&"./new.py".to_string()));
    }

    #[test]
    fn parse_renames_adds_dot_slash_when_missing() {
        let text = "R100\told.py\tnew.py\n";
        let map = parse_renames(text);
        assert_eq!(map.get("./old.py"), Some(&"./new.py".to_string()));
    }

    #[test]
    fn parse_renames_handles_mixed_prefixes() {
        let text = "R090\told.py\t./new.py\n";
        let map = parse_renames(text);
        assert_eq!(map.get("./old.py"), Some(&"./new.py".to_string()));
    }

    #[test]
    fn parse_renames_skips_non_rename_lines() {
        let text = "M\tunchanged.py\nA\tnew.py\nR100\told.py\tnewest.py\n";
        let map = parse_renames(text);
        assert_eq!(map.len(), 1);
        assert!(map.contains_key("./old.py"));
    }

    #[test]
    fn parse_renames_empty_input() {
        assert!(parse_renames("").is_empty());
    }

    #[test]
    fn parse_git_root_stdout_handles_empty_output() {
        assert!(parse_git_root_stdout("").is_none());
        assert!(parse_git_root_stdout("   \n").is_none());
    }

    #[test]
    fn parse_git_root_stdout_returns_trimmed_path() {
        assert_eq!(
            parse_git_root_stdout("/repo/root\n"),
            Some(PathBuf::from("/repo/root"))
        );
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
