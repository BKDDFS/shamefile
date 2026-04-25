use crate::languages::Language;
use crate::scanner::Violation;
use std::ops::Range;
use tree_sitter::{Parser, Tree};

/// Filter out violations where the matched token is not inside a comment.
///
/// Uses tree-sitter to parse the source and identify comment byte ranges.
/// Keeps only violations where at least one occurrence of the token falls
/// inside a comment. If parsing fails or yields ERROR nodes, returns all
/// violations unchanged (graceful degradation — an unclosed `/* */` block
/// would otherwise misclassify code as comments).
pub fn filter_non_comments(
    source: &str,
    lang: &Language,
    violations: Vec<Violation>,
) -> Vec<Violation> {
    if violations.is_empty() {
        return violations;
    }

    match build_tree(source, lang) {
        Some(tree) if !tree.root_node().has_error() => {
            filter_with_tree(source, lang, &tree, violations)
        }
        _ => violations,
    }
}

fn build_tree(source: &str, lang: &Language) -> Option<Tree> {
    let mut parser = Parser::new();
    parser.set_language(&(lang.grammar)()).ok()?;
    parser.parse(source, None)
}

fn filter_with_tree(
    source: &str,
    lang: &Language,
    tree: &Tree,
    violations: Vec<Violation>,
) -> Vec<Violation> {
    let mut comment_ranges = Vec::new();
    collect_node_ranges(tree.root_node(), lang.comment_types, &mut comment_ranges);

    let line_offsets = build_line_offsets(source);

    violations
        .into_iter()
        .filter(|v| {
            let line_start = line_offsets
                .get((v.line_number as usize).wrapping_sub(1))
                .copied()
                .unwrap_or(0);

            let line_lower = v.line_content.to_ascii_lowercase();
            let token_lower = v.matched_token.to_ascii_lowercase();

            // Find ALL positions of the token in the line.
            // Keep if at least one occurrence is inside a comment.
            let mut search_from = 0;
            while let Some(col) = line_lower[search_from..].find(&token_lower) {
                let abs_offset = line_start + search_from + col;
                if is_in_range(abs_offset, &comment_ranges) {
                    return true;
                }
                search_from += col + 1;
            }

            false
        })
        .collect()
}

fn collect_node_ranges(
    node: tree_sitter::Node,
    target_types: &[&str],
    ranges: &mut Vec<Range<usize>>,
) {
    if target_types.contains(&node.kind()) {
        ranges.push(node.start_byte()..node.end_byte());
        return;
    }

    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_node_ranges(child, target_types, ranges);
    }
}

fn build_line_offsets(source: &str) -> Vec<usize> {
    let mut offsets = vec![0];
    for (i, byte) in source.bytes().enumerate() {
        if byte == b'\n' {
            offsets.push(i + 1);
        }
    }
    offsets
}

fn is_in_range(offset: usize, ranges: &[Range<usize>]) -> bool {
    ranges.iter().any(|r| r.contains(&offset))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::languages::Language;

    fn make_violation(line_number: u32, line_content: &str, matched_token: &str) -> Violation {
        Violation {
            path: std::path::PathBuf::from("test.py"),
            line_number,
            line_content: line_content.to_string(),
            matched_token: matched_token.to_string(),
        }
    }

    fn python() -> &'static Language {
        Language::for_extension("py").unwrap()
    }

    fn javascript() -> &'static Language {
        Language::for_extension("js").unwrap()
    }

    fn typescript() -> &'static Language {
        Language::for_extension("ts").unwrap()
    }

    #[test]
    fn python_string_filtered() {
        let source = "msg = \"use # noqa to suppress warnings\"\n";
        let violations = vec![make_violation(1, source.trim(), "# noqa")];

        let result = filter_non_comments(source, python(), violations);

        assert!(result.is_empty());
    }

    #[test]
    fn python_comment_kept() {
        let source = "x = 1  # noqa\n";
        let violations = vec![make_violation(1, "x = 1  # noqa", "# noqa")];

        let result = filter_non_comments(source, python(), violations);

        assert_eq!(result.len(), 1);
    }

    #[test]
    fn python_docstring_filtered() {
        let source = "def foo():\n    \"\"\"Use # noqa for suppression.\"\"\"\n    pass\n";
        let violations = vec![make_violation(
            2,
            "    \"\"\"Use # noqa for suppression.\"\"\"",
            "# noqa",
        )];

        let result = filter_non_comments(source, python(), violations);

        assert!(result.is_empty());
    }

    #[test]
    fn python_multiline_string_filtered() {
        let source = "msg = \"\"\"\nuse # noqa to suppress\nwarnings\n\"\"\"\n";
        let violations = vec![make_violation(2, "use # noqa to suppress", "# noqa")];

        let result = filter_non_comments(source, python(), violations);

        assert!(result.is_empty());
    }

    #[test]
    fn js_template_literal_filtered() {
        let source = "const msg = `add // eslint-disable above the line`;\n";
        let violations = vec![make_violation(1, source.trim(), "// eslint-disable")];

        let result = filter_non_comments(source, javascript(), violations);

        assert!(result.is_empty());
    }

    #[test]
    fn js_string_filtered() {
        let source = "const msg = \"add // eslint-disable above the line\";\n";
        let violations = vec![make_violation(1, source.trim(), "// eslint-disable")];

        let result = filter_non_comments(source, javascript(), violations);

        assert!(result.is_empty());
    }

    #[test]
    fn js_comment_kept() {
        let source = "// eslint-disable-next-line no-var\nvar x = 1;\n";
        let violations = vec![make_violation(
            1,
            "// eslint-disable-next-line no-var",
            "// eslint-disable",
        )];

        let result = filter_non_comments(source, javascript(), violations);

        assert_eq!(result.len(), 1);
    }

    #[test]
    fn ts_string_filtered() {
        let source = "const msg: string = \"use // @ts-ignore for escape hatch\";\n";
        let violations = vec![make_violation(1, source.trim(), "// @ts-ignore")];

        let result = filter_non_comments(source, typescript(), violations);

        assert!(result.is_empty());
    }

    #[test]
    fn token_in_string_and_comment_same_line_kept() {
        let source = "msg = \"# noqa\"  # noqa\n";
        let violations = vec![make_violation(1, "msg = \"# noqa\"  # noqa", "# noqa")];

        let result = filter_non_comments(source, python(), violations);

        assert_eq!(result.len(), 1);
    }

    #[test]
    fn syntax_error_graceful_degradation() {
        let source = "def foo(\n    x = 1  # noqa\n";
        let violations = vec![make_violation(2, "    x = 1  # noqa", "# noqa")];

        let result = filter_non_comments(source, python(), violations);

        assert_eq!(result.len(), 1);
    }
}
