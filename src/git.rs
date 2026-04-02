use std::process::Command;

/// Fetch the current git user and email.
/// Returns "Name <email>" or "Unknown" if git is not configured.
pub fn get_git_author() -> String {
    let name = get_git_config("user.name").unwrap_or_else(|| "Unknown".to_string());
    let email = get_git_config("user.email").unwrap_or_else(|| "unknown@example.com".to_string());

    if name == "Unknown" && email == "unknown@example.com" {
        return "Unknown".to_string();
    }

    format!("{} <{}>", name, email)
}

fn get_git_config(key: &str) -> Option<String> {
    let output = Command::new("git")
        .arg("config")
        .arg("--get")
        .arg(key)
        .output()
        .ok()?;

    if output.status.success() {
        let val = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if val.is_empty() { None } else { Some(val) }
    } else {
        None
    }
}
