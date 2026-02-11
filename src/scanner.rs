use crate::ShamefileError;
use crate::tokens::get_token_regex;
use grep::regex::RegexMatcher;
use grep::searcher::sinks::UTF8;
use grep::searcher::Searcher;
use ignore::WalkBuilder;
use std::path::{Path, PathBuf};

/// Represents a raw violation found in the codebase.
#[derive(Debug)]
pub struct Violation {
    pub path: PathBuf,
    pub line_number: u64,
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
        if !entry.file_type().map_or(false, |ft| ft.is_file()) {
            continue;
        }

        let path = entry.path();
        
        // Use a sink to collect matches for this file
        let sink = UTF8(|lnum, line| {
             // Find which token matched
             // Since we use regex like `(# noqa|# NOSONAR)`, we can just check which one is present
             // Optimization: We could use `matcher` to find the match within `line`, 
             // but simple string contains is fast enough for the sink callback since regex already confirmed a match.
             
             let token = crate::tokens::TRACKED_TOKENS.iter()
                .find(|&&t| line.contains(t))
                .unwrap_or(&"UNKNOWN")
                .to_string();

            violations.push(Violation {
                path: path.to_path_buf(),
                line_number: lnum,
                line_content: line.to_string(),
                matched_token: token,
            });
            Ok(true)
        });

        if let Err(e) = searcher.search_path(&matcher, path, sink) {
            // We ignore IO errors for individual files to keep scanning others?
            // Or return error? For a linter, usually we want to know if we can't read a file.
            // But let's just log it or wrap it.
            // For now, let's propagate as IO Error via ScanError
            return Err(ShamefileError::ScanError(e.into()));
        }
    }

    Ok(violations)
}
