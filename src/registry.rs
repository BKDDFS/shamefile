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
    #[serde(
        deserialize_with = "deserialize_created_at",
        serialize_with = "serialize_created_at"
    )]
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

fn serialize_created_at<S>(dt: &DateTime<Utc>, serializer: S) -> Result<S::Ok, S::Error>
where
    S: serde::Serializer,
{
    serializer.serialize_str(&dt.format("%Y-%m-%d").to_string())
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
        let normalized = file.replace('\\', "/");
        if normalized.starts_with("./") || normalized.starts_with('/') {
            format!("{normalized}:{line}")
        } else {
            format!("./{normalized}:{line}")
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
        // Pre-process: quote unquoted plain-scalar why values so YAML parser
        // doesn't eat comments (`# TODO`), interpret keywords, etc.
        let content = quote_unquoted_why_values(&content);
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
        // Normalize why: replace newlines with spaces, collapse consecutive whitespace runs
        // that crossed newlines, and trim. Preserves intentional multi-spaces within a line.
        for entry in self.entries.iter_mut() {
            if entry.why.contains('\n') {
                entry.why = entry.why.replace('\n', " ").trim().to_string();
            }
        }
        self.entries.sort_by(|a, b| {
            a.file()
                .cmp(b.file())
                .then(a.line().cmp(&b.line()))
                .then(a.token.cmp(&b.token))
        });
        let content = serde_yaml::to_string(self)?;
        // Add blank line between entries for readability
        let content = content.replace("\n- location:", "\n\n- location:");
        // Indent sequences first (yamllint default: indent-sequences: true).
        // After this, why: is at column 4 (under `  - location:` at column 2).
        let content = indent_sequences(&content);
        // Normalize why: force-quote unquoted values, fold long lines to >-.
        // Runs after indent_sequences so fold content indentation is correct.
        let content = content
            .lines()
            .flat_map(normalize_why_line)
            .collect::<Vec<_>>()
            .join("\n");
        // Prepend yamllint disable-file directive so users with strict yamllint
        // configs don't get noise from this file, then add document start marker.
        let content = format!("# yamllint disable-file\n---\n{}\n", content.trim_end());
        fs::write(path, content).map_err(ShamefileError::RegistryWriteError)?;
        Ok(())
    }
}

const MAX_LINE_LENGTH: usize = 80;

/// Indent sequence entries (yamllint `indent-sequences: true` default).
/// Shifts every non-empty line after `entries:` right by 2 spaces.
fn indent_sequences(content: &str) -> String {
    let mut in_entries = false;
    content
        .lines()
        .map(|line| {
            if line == "entries:" || line.starts_with("entries:") {
                in_entries = true;
                line.to_string()
            } else if in_entries && !line.is_empty() {
                format!("  {line}")
            } else {
                line.to_string()
            }
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Strip the `why: ` prefix at any indentation level. Returns (indent, value).
fn strip_why_prefix(line: &str) -> Option<(&str, &str)> {
    let trimmed = line.trim_start();
    let rest = trimmed.strip_prefix("why: ")?;
    let indent_len = line.len() - trimmed.len();
    Some((&line[..indent_len], rest))
}

/// Pre-process raw YAML before parsing: quote unquoted plain-scalar `why:` values.
/// This prevents YAML from eating `# TODO` as a comment and from misinterpreting
/// ambiguous values. Leaves already-quoted, block-scalar, and null-like values alone.
fn quote_unquoted_why_values(content: &str) -> String {
    content
        .lines()
        .map(|line| {
            let Some((indent, rest)) = strip_why_prefix(line) else {
                return line.to_string();
            };
            let value = rest.trim_end();
            if value.is_empty()
                || value.starts_with('\'')
                || value.starts_with('"')
                || value.starts_with('|')
                || value.starts_with('>')
                || value.starts_with('!')  // YAML type tag like !!str
                || value == "null"
                || value == "~"
                || value == "Null"
                || value == "NULL"
            {
                return line.to_string();
            }
            format!("{indent}why: '{}'", value.replace('\'', "''"))
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Normalize a single `why:` line: force-quote unquoted values, fold if too long.
/// Returns one or more output lines (multiple when folded to `>-` block).
fn normalize_why_line(line: &str) -> Vec<String> {
    let Some((indent, value)) = strip_why_prefix(line) else {
        return vec![line.to_string()];
    };

    let quoted_line = if value.starts_with('\'')
        || value.starts_with('"')
        || value.starts_with('|')
        || value.starts_with('>')
    {
        line.to_string()
    } else {
        format!("{indent}why: '{}'", value.replace('\'', "''"))
    };

    if quoted_line.len() <= MAX_LINE_LENGTH {
        return vec![quoted_line];
    }

    // Fold to `>-` block. Extract the raw value (stripping single quotes + unescape).
    let value_part = quoted_line
        .strip_prefix(indent)
        .and_then(|s| s.strip_prefix("why: "))
        .unwrap_or(&quoted_line);
    let raw_value = if value_part.starts_with('\'') && value_part.ends_with('\'') {
        value_part[1..value_part.len() - 1].replace("''", "'")
    } else {
        value_part.to_string()
    };

    let mut out = vec![format!("{indent}why: >-")];
    let fold_indent = format!("{indent}  ");
    let max_content_len = MAX_LINE_LENGTH - fold_indent.len();
    let mut current = String::new();
    for word in raw_value.split(' ') {
        if current.is_empty() {
            current.push_str(word);
        } else if current.len() + 1 + word.len() <= max_content_len {
            current.push(' ');
            current.push_str(word);
        } else {
            out.push(format!("{fold_indent}{current}"));
            current = word.to_string();
        }
    }
    if !current.is_empty() {
        out.push(format!("{fold_indent}{current}"));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn content_hash_trims_whitespace() {
        assert_eq!(content_hash("  foo  "), "foo");
        assert_eq!(content_hash("\t\nbar\n"), "bar");
    }

    #[test]
    fn content_hash_preserves_internal_whitespace() {
        assert_eq!(content_hash("  a  b  "), "a  b");
    }

    #[test]
    fn content_hash_empty() {
        assert_eq!(content_hash("   \t\n"), "");
    }

    #[test]
    fn extract_entry_start_lines_basic() {
        let yaml = "\
config: {}
entries:
- location: ./a.py:1
  token: \"# noqa\"
- location: ./b.py:2
  token: \"# noqa\"
";
        assert_eq!(extract_entry_start_lines(yaml), vec![3, 5]);
    }

    #[test]
    fn extract_entry_start_lines_empty_when_no_entries_section() {
        let yaml = "config: {}\n";
        assert!(extract_entry_start_lines(yaml).is_empty());
    }

    #[test]
    fn extract_entry_start_lines_stops_at_next_top_level_key() {
        let yaml = "\
entries:
- location: ./a.py:1
other:
- location: ./should_not_match.py:1
";
        assert_eq!(extract_entry_start_lines(yaml), vec![2]);
    }

    #[test]
    fn deserialize_created_at_accepts_rfc3339() {
        let parsed: EntryStub =
            serde_yaml::from_str("created_at: \"2024-01-15T10:30:00Z\"").unwrap();
        assert_eq!(parsed.created_at.to_rfc3339(), "2024-01-15T10:30:00+00:00");
    }

    #[test]
    fn deserialize_created_at_accepts_date_only() {
        let parsed: EntryStub = serde_yaml::from_str("created_at: \"2024-01-15\"").unwrap();
        assert_eq!(parsed.created_at.to_rfc3339(), "2024-01-15T00:00:00+00:00");
    }

    #[test]
    fn deserialize_created_at_rejects_garbage() {
        let err = serde_yaml::from_str::<EntryStub>("created_at: \"not a date\"").unwrap_err();
        assert!(err.to_string().contains("invalid created_at"));
    }

    #[test]
    fn deserialize_why_treats_missing_as_empty() {
        let parsed: WhyStub = serde_yaml::from_str("why: null").unwrap();
        assert_eq!(parsed.why, "");
    }

    #[test]
    fn deserialize_why_passes_through_strings() {
        let parsed: WhyStub = serde_yaml::from_str("why: 'because reasons'").unwrap();
        assert_eq!(parsed.why, "because reasons");
    }

    #[test]
    fn entry_file_and_line_split_on_colon() {
        let e = make_entry("./src/foo.py:42", "# noqa");
        assert_eq!(e.file(), "./src/foo.py");
        assert_eq!(e.line(), 42);
    }

    #[test]
    fn entry_line_returns_zero_for_unparseable() {
        let e = make_entry("./src/foo.py:not_a_number", "# noqa");
        assert_eq!(e.line(), 0);
    }

    #[test]
    fn make_location_normalizes_windows_separators() {
        assert_eq!(Entry::make_location("src\\foo.py", 7), "./src/foo.py:7");
    }

    #[test]
    fn make_location_preserves_dot_slash() {
        assert_eq!(Entry::make_location("./src/foo.py", 7), "./src/foo.py:7");
    }

    #[test]
    fn make_location_preserves_absolute_path() {
        assert_eq!(Entry::make_location("/abs/foo.py", 7), "/abs/foo.py:7");
    }

    #[test]
    fn registry_default_is_empty() {
        let r = Registry::default();
        assert!(r.entries.is_empty());
    }

    #[test]
    fn load_reports_flow_style_duplicates_without_line_refs() {
        // Flow-style entries don't produce `- location:` lines, so
        // extract_entry_start_lines returns an empty Vec — this hits the
        // `refs.is_empty()` branch in the duplicate-error formatter.
        let yaml = "\
config: {}
entries: [{location: ./a.py:1, token: \"# noqa\", content: x, created_at: \"2024-01-15\", owner: a, why: w}, {location: ./a.py:1, token: \"# noqa\", content: x, created_at: \"2024-01-15\", owner: a, why: w}]
";
        let tmp = tempfile::NamedTempFile::new().unwrap();
        std::fs::write(tmp.path(), yaml).unwrap();
        let err = Registry::load(tmp.path()).unwrap_err();
        let msg = err.to_string();
        assert!(msg.contains("duplicates"), "got: {msg}");
        // No line refs because flow-style YAML has no `- location:` markers.
        assert!(!msg.contains(":2"), "got: {msg}");
    }

    #[test]
    fn normalize_why_line_folds_long_double_quoted_value() {
        // A double-quoted long value isn't re-wrapped in single quotes, so
        // the folding path takes the `value_part.to_string()` branch.
        let long = "x".repeat(120);
        let line = format!("  why: \"{long}\"");
        let folded = normalize_why_line(&line);
        assert!(folded.len() > 1, "expected folded output, got: {folded:?}");
        assert_eq!(folded[0], "  why: >-");
    }

    #[test]
    fn normalize_why_line_passes_through_non_why_lines() {
        let lines = normalize_why_line("  location: ./a.py:1");
        assert_eq!(lines, vec!["  location: ./a.py:1".to_string()]);
    }

    #[derive(Debug, Deserialize)]
    struct EntryStub {
        #[serde(deserialize_with = "deserialize_created_at")]
        created_at: DateTime<Utc>,
    }

    #[derive(Deserialize)]
    struct WhyStub {
        #[serde(deserialize_with = "deserialize_why")]
        why: String,
    }

    fn make_entry(location: &str, token: &str) -> Entry {
        Entry {
            location: location.to_string(),
            token: token.to_string(),
            content: String::new(),
            created_at: Utc.with_ymd_and_hms(2024, 1, 1, 0, 0, 0).unwrap(),
            owner: String::new(),
            why: String::new(),
        }
    }
}
