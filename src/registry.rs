use crate::ShamefileError;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
pub struct Registry {
    /// Configuration for the registry
    #[serde(default)]
    pub config: Config,

    /// The list of known suppressions
    #[serde(default)]
    pub entries: Vec<Entry>,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct Config {}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Entry {
    pub location: String,
    pub token: String,

    pub owner: String,
    pub created_at: DateTime<Utc>,

    /// The reason why this suppression exists.
    /// If empty, it means justification is missing.
    #[serde(deserialize_with = "deserialize_why")]
    pub why: String,
}

fn deserialize_why<'de, D>(deserializer: D) -> Result<String, D::Error>
where
    D: serde::Deserializer<'de>,
{
    Ok(Option::<String>::deserialize(deserializer)?.unwrap_or_default())
}

impl Entry {
    pub fn file(&self) -> &str {
        self.location
            .rsplit_once(':')
            .map_or(&self.location, |(f, _)| f)
    }

    pub fn line(&self) -> u32 {
        self.location
            .rsplit_once(':')
            .and_then(|(_, l)| l.parse().ok())
            .unwrap_or(0)
    }

    pub fn make_location(file: &str, line: u32) -> String {
        format!("{}:{}", file, line)
    }
}

/// Returns the 1-indexed line number where each entry under `entries:` begins.
/// The result is parallel to `Vec<Entry>` produced by serde_yaml, since both
/// preserve sequence order. Used to point users at the duplicate row in
/// `shamefile.yaml` so the location is IDE-clickable.
fn extract_entry_start_lines(content: &str) -> Vec<usize> {
    let mut lines = Vec::new();
    let mut in_entries = false;

    for (i, line) in content.lines().enumerate() {
        let line_no = i + 1;
        let trimmed = line.trim_start();
        let indent = line.len() - trimmed.len();

        if indent == 0 && trimmed.starts_with("entries:") {
            in_entries = true;
            continue;
        }
        if in_entries && indent == 0 && !trimmed.is_empty() {
            in_entries = false;
            continue;
        }
        if in_entries && (trimmed.starts_with("- ") || trimmed == "-") {
            lines.push(line_no);
        }
    }
    lines
}

impl Default for Registry {
    fn default() -> Self {
        Self::new()
    }
}

impl Registry {
    pub fn new() -> Self {
        Registry {
            config: Config::default(),
            entries: Vec::new(),
        }
    }

    pub fn load(path: &Path) -> Result<Self, ShamefileError> {
        let content = fs::read_to_string(path).map_err(ShamefileError::RegistryReadError)?;
        let mut registry: Registry = serde_yaml::from_str(&content)?;
        for entry in &mut registry.entries {
            if let Some(stripped) = entry.location.strip_prefix("./") {
                entry.location = stripped.to_string();
            }
        }

        let entry_lines = extract_entry_start_lines(&content);
        let mut groups: BTreeMap<(&str, &str), Vec<usize>> = BTreeMap::new();
        for (idx, entry) in registry.entries.iter().enumerate() {
            let line_no = entry_lines.get(idx).copied().unwrap_or(0);
            groups
                .entry((entry.location.as_str(), entry.token.as_str()))
                .or_default()
                .push(line_no);
        }
        let path_display = path.display().to_string();
        let duplicates: Vec<String> = groups
            .into_iter()
            .filter(|(_, lines)| lines.len() > 1)
            .map(|((loc, tok), lines)| {
                let refs: Vec<String> = lines
                    .iter()
                    .map(|l| format!("{}:{}", path_display, l))
                    .collect();
                format!("'{}' at {} ({})", tok, loc, refs.join(", "))
            })
            .collect();
        if !duplicates.is_empty() {
            return Err(ShamefileError::DuplicateEntries(format!(
                "please remove duplicates from shamefile.yaml: {}",
                duplicates.join("; ")
            )));
        }

        Ok(registry)
    }

    pub fn save(&mut self, path: &Path) -> Result<(), ShamefileError> {
        self.entries.sort_by(|a, b| {
            a.file()
                .cmp(b.file())
                .then(a.line().cmp(&b.line()))
                .then(a.token.cmp(&b.token))
        });
        let content = serde_yaml::to_string(self)?;
        fs::write(path, content).map_err(ShamefileError::RegistryReadError)?;
        Ok(())
    }
}
