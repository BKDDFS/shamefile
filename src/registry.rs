use crate::ShamefileError;
use chrono::{DateTime, NaiveDate, TimeZone, Utc};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

pub fn content_hash(line: &str) -> String {
    line.trim().to_string()
}

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
    pub content: String,
    #[serde(deserialize_with = "deserialize_created_at")]
    pub created_at: DateTime<Utc>,
    pub owner: String,
    #[serde(deserialize_with = "deserialize_why")]
    pub why: String,
}

fn deserialize_created_at<'de, D>(deserializer: D) -> Result<DateTime<Utc>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let s = String::deserialize(deserializer)?;
    if let Ok(dt) = s.parse::<DateTime<Utc>>() {
        return Ok(dt);
    }
    if let Ok(date) = NaiveDate::parse_from_str(&s, "%Y-%m-%d")
        && let Some(dt) = date.and_hms_opt(0, 0, 0)
    {
        return Ok(Utc.from_utc_datetime(&dt));
    }
    Err(serde::de::Error::custom(format!(
        "invalid created_at: '{s}' — expected RFC 3339 (e.g. '2024-01-15T00:00:00Z') or date (e.g. '2024-01-15')"
    )))
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
        if file.starts_with("./") || file.starts_with('/') {
            format!("{file}:{line}")
        } else {
            format!("./{file}:{line}")
        }
    }
}

/// Returns the 1-indexed line number where each entry under `entries:` begins.
/// The result is parallel to `Vec<Entry>` produced by serde_yaml, since both
/// preserve sequence order. Used to point users at the duplicate row in
/// `shamefile.yaml` so the location is IDE-clickable.
pub fn extract_entry_start_lines(content: &str) -> Vec<usize> {
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
        if in_entries && indent == 0 && !trimmed.is_empty() && !trimmed.starts_with("- ") {
            in_entries = false;
            continue;
        }
        if in_entries && trimmed.starts_with("- location:") {
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
        let registry: Registry = serde_yaml::from_str(&content)?;

        let entry_lines = extract_entry_start_lines(&content);
        let mut groups: BTreeMap<(&str, &str), Vec<Option<usize>>> = BTreeMap::new();
        for (idx, entry) in registry.entries.iter().enumerate() {
            let line_no = entry_lines.get(idx).copied();
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
                    .filter_map(|l| l.map(|n| format!("{}:{}", path_display, n)))
                    .collect();
                if refs.is_empty() {
                    format!("'{}' at {}", tok, loc)
                } else {
                    format!("'{}' at {} ({})", tok, loc, refs.join(", "))
                }
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
        // Add blank line between entries for readability
        let content = content.replace("\n- location:", "\n\n- location:");
        // Force-quote why values that serde_yaml left unquoted
        let content = content
            .lines()
            .map(|line| {
                if let Some(value) = line.strip_prefix("  why: ") {
                    if value.starts_with('\'')
                        || value.starts_with('"')
                        || value.starts_with('|')
                        || value.starts_with('>')
                    {
                        line.to_string()
                    } else {
                        format!("  why: '{}'", value.replace('\'', "''"))
                    }
                } else {
                    line.to_string()
                }
            })
            .collect::<Vec<_>>()
            .join("\n");
        fs::write(path, content).map_err(ShamefileError::RegistryWriteError)?;
        Ok(())
    }
}
