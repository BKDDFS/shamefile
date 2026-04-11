use crate::ShamefileError;
use crate::tokens::get_token_regex;
use grep::regex::RegexMatcher;
use grep::searcher::Searcher;
use grep::searcher::sinks::UTF8;
use ignore::WalkBuilder;
use std::path::{Path, PathBuf};

/// Represents a raw violation found in the codebase.
#[derive(Debug)]
pub struct Violation {
    pub path: PathBuf,
    pub line_number: u32,
    pub line_content: String,
    pub matched_token: String,
}

/// Scan a directory for tracked tokens.
pub fn scan(root_path: &Path) -> Result<Vec<Violation>, ShamefileError> {
    let pattern = get_token_regex();
    let matcher = RegexMatcher::new(&pattern)?;
    let mut searcher = Searcher::new();
    let mut violations = Vec::new();

    let walker = WalkBuilder::new(root_path).build();

    for result in walker {
        let entry = result?;
        if !entry.file_type().is_some_and(|ft| ft.is_file()) {
            continue;
        }

        let path = entry.path();

        // Use a sink to collect matches for this file
        let sink = UTF8(|lnum, line| {
            // Find which token matched
            // Since we use regex like `(# noqa|# NOSONAR)`, we can just check which one is present
            // Optimization: We could use `matcher` to find the match within `line`,
            // but simple string contains is fast enough for the sink callback since regex already confirmed a match.

            for token in crate::tokens::TRACKED_TOKENS
                .iter()
                .filter(|&&t| line.to_ascii_lowercase().contains(&t.to_ascii_lowercase()))
            {
                violations.push(Violation {
                    path: path.to_path_buf(),
                    line_number: lnum as u32,
                    line_content: line.to_string(),
                    matched_token: token.to_string(),
                });
            }
            Ok(true)
        });

        if let Err(e) = searcher.search_path(&matcher, path, sink) {
            eprintln!("Warning: skipping {}: {}", path.display(), e);
        }
    }

    Ok(violations)
}
