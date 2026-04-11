from conftest import LANGUAGES, parse_languages_from_rust_source


def test_parse_languages_sanity():
    """Parsing languages.rs should return all expected languages."""
    languages = parse_languages_from_rust_source()
    assert len(languages) > 0
    assert "Python" in languages
    assert "JavaScript" in languages
    assert "TypeScript" in languages


def test_tokens_match_per_language():
    """Tokens defined in Python tests must match tokens in languages.rs per language."""
    rust_languages = parse_languages_from_rust_source()
    for name, expected in LANGUAGES.items():
        assert name in rust_languages, f"Language '{name}' missing from languages.rs"
        assert sorted(rust_languages[name]["tokens"]) == sorted(expected["tokens"]), (
            f"Token mismatch for {name}:\n"
            f"  Rust:  {sorted(rust_languages[name]['tokens'])}\n"
            f"  Tests: {sorted(expected['tokens'])}"
        )


def test_extensions_match_per_language():
    """Extensions defined in Python tests must match extensions in languages.rs per language."""
    rust_languages = parse_languages_from_rust_source()
    for name, expected in LANGUAGES.items():
        assert name in rust_languages, f"Language '{name}' missing from languages.rs"
        assert sorted(rust_languages[name]["extensions"]) == sorted(expected["extensions"]), (
            f"Extension mismatch for {name}:\n"
            f"  Rust:  {sorted(rust_languages[name]['extensions'])}\n"
            f"  Tests: {sorted(expected['extensions'])}"
        )


def test_no_extra_languages_in_rust():
    """Every language in languages.rs must be covered by Python tests."""
    rust_languages = parse_languages_from_rust_source()
    for name in rust_languages:
        assert name in LANGUAGES, f"Language '{name}' is in languages.rs but not in test LANGUAGES"
