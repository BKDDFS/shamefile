use regex_syntax;

pub const TRACKED_TOKENS: &[&str] = &[
    // Python
    "# noqa",             // Flake8 / Ruff
    "# pylint: disable",  // Pylint
    "# type: ignore",     // Mypy
    "# pyright: ignore",  // Pyright
    "# pytype: disable",  // Pytype
    "# pyre-ignore",      // Pyre
    "# pyre-fixme",       // Pyre
    "# nosec",            // Bandit
    "# pragma: no cover", // Coverage.py
    "# fmt: off",         // Black / Ruff
    "# fmt: skip",        // Black / Ruff
    "# isort: skip",      // isort
    "# lint-fixme",       // Fixit
    "# lint-ignore",      // Fixit
    "# autopep8: off",    // autopep8
    // JavaScript
    "// eslint-disable", // ESLint (line)
    "/* eslint-disable", // ESLint (block)
    "// tslint:disable", // TSLint (line)
    "/* tslint:disable", // TSLint (block)
    // TypeScript
    "// @ts-ignore",       // TypeScript (line)
    "/* @ts-ignore",       // TypeScript (block/JSX)
    "// @ts-expect-error", // TypeScript (line)
    "/* @ts-expect-error", // TypeScript (block/JSX)
];

/// Returns the regex pattern to search for any of these tokens.
pub fn get_token_regex() -> String {
    let patterns: Vec<String> = TRACKED_TOKENS
        .iter()
        .map(|&t| regex_syntax::escape(t))
        .collect();
    format!("(?i)({})", patterns.join("|"))
}

#[cfg(any())] // Disabled vibecoded tests
mod _vibecoded_tests {
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
