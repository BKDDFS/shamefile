pub struct Language {
    pub name: &'static str,
    pub extensions: &'static [&'static str],
    pub tokens: &'static [&'static str],
    pub grammar: fn() -> tree_sitter::Language,
    pub comment_types: &'static [&'static str],
}

impl Language {
    pub fn for_extension(ext: &str) -> Option<&'static Language> {
        LANGUAGES.iter().find(|l| l.extensions.contains(&ext))
    }

    pub fn token_regex(&self) -> String {
        let patterns: Vec<String> = self
            .tokens
            .iter()
            .map(|t| regex_syntax::escape(t))
            .collect();
        format!("(?i)({})", patterns.join("|"))
    }
}

pub static LANGUAGES: &[Language] = &[
    Language {
        name: "Python",
        extensions: &["py"],
        grammar: || tree_sitter_python::LANGUAGE.into(),
        comment_types: &["comment"],
        tokens: &[
            "# noqa",             // Flake8 / Ruff
            "# pylint: disable",  // Pylint
            "# type: ignore",     // Mypy
            "# pyright: ignore",  // Pyright
            "# pytype: disable",  // Pytype
            "# pyre-ignore",      // Pyre
            "# pyre-fixme",       // Pyre
            "nosec",              // Bandit
            "# pragma: no cover", // Coverage.py
            "# fmt: off",         // Black / Ruff
            "# fmt: skip",        // Black / Ruff
            "# isort: skip",      // isort
            "# lint-fixme",       // Fixit
            "# lint-ignore",      // Fixit
            "# autopep8: off",    // autopep8
        ],
    },
    Language {
        name: "JavaScript",
        extensions: &["js", "jsx", "mjs", "cjs"],
        grammar: || tree_sitter_javascript::LANGUAGE.into(),
        comment_types: &["comment"],
        tokens: &[
            "// eslint-disable",   // ESLint (line)
            "/* eslint-disable",   // ESLint (block)
            "// @ts-ignore",       // TypeScript (line, via checkJs)
            "/* @ts-ignore",       // TypeScript (block, via checkJs)
            "// @ts-expect-error", // TypeScript (line, via checkJs)
            "/* @ts-expect-error", // TypeScript (block, via checkJs)
        ],
    },
    Language {
        name: "TypeScript",
        extensions: &["ts"],
        grammar: || tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into(),
        comment_types: &["comment"],
        tokens: &[
            "// eslint-disable",   // ESLint (line)
            "/* eslint-disable",   // ESLint (block)
            "// tslint:disable",   // TSLint (line)
            "/* tslint:disable",   // TSLint (block)
            "// @ts-ignore",       // TypeScript (line)
            "/* @ts-ignore",       // TypeScript (block/JSX)
            "// @ts-expect-error", // TypeScript (line)
            "/* @ts-expect-error", // TypeScript (block/JSX)
        ],
    },
    Language {
        name: "TypeScript (TSX)",
        extensions: &["tsx"],
        grammar: || tree_sitter_typescript::LANGUAGE_TSX.into(),
        comment_types: &["comment"],
        tokens: &[
            "// eslint-disable",   // ESLint (line)
            "/* eslint-disable",   // ESLint (block)
            "// tslint:disable",   // TSLint (line)
            "/* tslint:disable",   // TSLint (block)
            "// @ts-ignore",       // TypeScript (line)
            "/* @ts-ignore",       // TypeScript (block/JSX)
            "// @ts-expect-error", // TypeScript (line)
            "/* @ts-expect-error", // TypeScript (block/JSX)
        ],
    },
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn python_found_by_extension() {
        let lang = Language::for_extension("py").expect("Python not found");
        assert_eq!(lang.name, "Python");
    }

    #[test]
    fn javascript_found_by_extension() {
        let lang = Language::for_extension("js").expect("JavaScript not found");
        assert_eq!(lang.name, "JavaScript");
    }

    #[test]
    fn javascript_jsx_extension() {
        let lang = Language::for_extension("jsx").expect("jsx not found");
        assert_eq!(lang.name, "JavaScript");
    }

    #[test]
    fn javascript_mjs_extension() {
        let lang = Language::for_extension("mjs").expect("mjs not found");
        assert_eq!(lang.name, "JavaScript");
    }

    #[test]
    fn javascript_cjs_extension() {
        let lang = Language::for_extension("cjs").expect("cjs not found");
        assert_eq!(lang.name, "JavaScript");
    }

    #[test]
    fn typescript_found_by_extension() {
        let lang = Language::for_extension("ts").expect("TypeScript not found");
        assert_eq!(lang.name, "TypeScript");
    }

    #[test]
    fn typescript_tsx_extension() {
        let lang = Language::for_extension("tsx").expect("tsx not found");
        assert_eq!(lang.name, "TypeScript (TSX)");
    }

    #[test]
    fn token_regex_matches_own_tokens() {
        let re = regex::Regex::new(&Language::for_extension("py").unwrap().token_regex()).unwrap();
        assert!(re.is_match("x = 1  # noqa"));
        assert!(re.is_match("# type: ignore[misc]"));
        assert!(!re.is_match("// eslint-disable-next-line"));
        assert!(!re.is_match("just some code"));
    }

    #[test]
    fn token_regex_is_case_insensitive() {
        let re = regex::Regex::new(&Language::for_extension("py").unwrap().token_regex()).unwrap();
        assert!(re.is_match("# NOQA"));
        assert!(re.is_match("# Pragma: No Cover"));
    }

    #[test]
    fn unsupported_extension_returns_none() {
        assert!(Language::for_extension("md").is_none());
        assert!(Language::for_extension("json").is_none());
        assert!(Language::for_extension("").is_none());
    }

    #[test]
    fn every_language_has_tokens() {
        for lang in LANGUAGES {
            assert!(!lang.tokens.is_empty(), "{} has no tokens", lang.name);
        }
    }

    /// Returns the first extension claimed by two different languages, paired
    /// with both language names. Takes (name, extensions) tuples so tests can
    /// pass synthetic data without constructing full `Language` values.
    fn first_duplicate_extension<'a>(
        langs: impl IntoIterator<Item = (&'a str, &'a [&'a str])>,
    ) -> Option<(&'a str, &'a str, &'a str)> {
        let mut seen = std::collections::HashMap::new();
        for (name, extensions) in langs {
            for ext in extensions {
                if let Some(other) = seen.insert(*ext, name) {
                    return Some((ext, other, name));
                }
            }
        }
        None
    }

    #[test]
    fn no_duplicate_extensions_across_languages() {
        let langs = LANGUAGES.iter().map(|l| (l.name, l.extensions));
        assert_eq!(first_duplicate_extension(langs), None);
    }

    #[test]
    fn first_duplicate_extension_finds_collision() {
        let langs = [("A", &["xx"][..]), ("B", &["xx"][..])];
        assert_eq!(first_duplicate_extension(langs), Some(("xx", "A", "B")));
    }

    #[test]
    fn python_has_noqa_but_not_eslint() {
        let lang = Language::for_extension("py").unwrap();
        assert!(lang.tokens.contains(&"# noqa"));
        assert!(!lang.tokens.contains(&"// eslint-disable"));
    }

    #[test]
    fn javascript_has_eslint_and_ts_ignore_but_not_noqa() {
        let lang = Language::for_extension("js").unwrap();
        assert!(lang.tokens.contains(&"// eslint-disable"));
        assert!(lang.tokens.contains(&"// @ts-ignore"));
        assert!(lang.tokens.contains(&"// @ts-expect-error"));
        assert!(!lang.tokens.contains(&"# noqa"));
    }

    #[test]
    fn typescript_has_ts_ignore_and_eslint() {
        let lang = Language::for_extension("ts").unwrap();
        assert!(lang.tokens.contains(&"// @ts-ignore"));
        assert!(lang.tokens.contains(&"// eslint-disable"));
    }
}
