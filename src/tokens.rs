use regex_syntax;

/// The list of tokens that we search for in the codebase.
/// These are currently hardcoded as per the design requirements.
pub const TRACKED_TOKENS: &[&str] = &[
    "# noqa",
    "# NOSONAR",
    "# pragma: no cover",
    "// pylint: disable",
    "// eslint-disable",
    "// tslint:disable",
    "// @ts-ignore",
    "// @ts-expect-error",
];

/// Returns the regex pattern to search for any of these tokens.
/// This constructs a pattern like `(# noqa|# NOSONAR|...)` for use with grep.
pub fn get_token_regex() -> String {
    let patterns: Vec<String> = TRACKED_TOKENS.iter().map(|&t| regex_syntax::escape(t)).collect();
    format!("({})", patterns.join("|"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use regex::Regex;

    #[test]
    fn test_regex_matches_all_tokens() {
        let pattern = get_token_regex();
        let re = Regex::new(&pattern).unwrap();

        for token in TRACKED_TOKENS {
            assert!(re.is_match(token), "Regex failed to match token: {}", token);
        }
    }

    #[test]
    fn test_regex_matches_in_context() {
        let pattern = get_token_regex();
        let re = Regex::new(&pattern).unwrap();

        assert!(re.is_match("x = 1 # noqa"));
        assert!(re.is_match("  // @ts-ignore: some reason"));
        assert!(re.is_match("foo(); // eslint-disable-line")); // Partial match due to simple contains
    }

    #[test]
    fn test_regex_does_not_match_other_things() {
        let pattern = get_token_regex();
        let re = Regex::new(&pattern).unwrap();

        assert!(!re.is_match("# random comment"));
        assert!(!re.is_match("// regular comment"));
    }
}
