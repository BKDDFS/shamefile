use crate::languages;
use ignore::WalkBuilder;
use regex::Regex;
use std::collections::HashSet;
use std::path::{Path, PathBuf};

/// Represents a raw violation found in the codebase.
#[derive(Debug)]
pub struct Violation {
    pub path: PathBuf,
    pub line_number: u32,
    pub line_content: String,
    pub matched_token: String,
}

pub struct ScanResult {
    pub violations: Vec<Violation>,
    pub scanned_files: HashSet<PathBuf>,
    pub skipped_files: HashSet<PathBuf>,
}

/// Scan a directory for tracked tokens.
pub fn scan(root_path: &Path, hidden: bool) -> Result<ScanResult, ignore::Error> {
    let mut violations = Vec::new();
    let mut scanned_files = HashSet::new();
    let mut skipped_files = HashSet::new();

    let lang_matchers: Vec<_> = languages::LANGUAGES
        .iter()
        .map(|lang| {
            let re = Regex::new(&lang.token_regex()).expect("Language token regex must compile");
            (lang, re)
        })
        .collect();

    let walker = WalkBuilder::new(root_path).hidden(!hidden).build();

    for result in walker {
        let entry = result?;
        if !entry.file_type().is_some_and(|ft| ft.is_file()) {
            continue;
        }

        let path = entry.path();
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
        let (lang, re) = match lang_matchers
            .iter()
            .find(|(l, _)| l.extensions.contains(&ext))
        {
            Some(pair) => pair,
            None => continue,
        };

        let content = match std::fs::read_to_string(path) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("Warning: skipping {}: {}", path.display(), e);
                skipped_files.insert(path.to_path_buf());
                continue;
            }
        };

        scanned_files.insert(path.to_path_buf());

        for (line_idx, line) in content.lines().enumerate() {
            if !re.is_match(line) {
                continue;
            }
            for token in lang
                .tokens
                .iter()
                .filter(|&&t| line.to_ascii_lowercase().contains(&t.to_ascii_lowercase()))
            {
                violations.push(Violation {
                    path: path.to_path_buf(),
                    line_number: (line_idx + 1) as u32,
                    line_content: line.to_string(),
                    matched_token: token.to_string(),
                });
            }
        }
    }

    Ok(ScanResult {
        violations,
        scanned_files,
        skipped_files,
    })
}
