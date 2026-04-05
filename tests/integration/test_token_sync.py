from conftest import ALL_TOKENS, parse_tokens_from_rust_source


def test_parse_tokens_from_rust_source_sanity():
    tokens = parse_tokens_from_rust_source()
    assert len(tokens) > 0
    assert "# noqa" in tokens


def test_all_test_tokens_exist_in_rust_source():
    rust_tokens = parse_tokens_from_rust_source()

    for token in ALL_TOKENS:
        assert token in rust_tokens, f"Token '{token}' is in tests but not in tokens.rs"


def test_all_rust_tokens_exist_in_tests():
    rust_tokens = parse_tokens_from_rust_source()

    for token in rust_tokens:
        assert token in ALL_TOKENS, f"Token '{token}' is in tokens.rs but not in tests"
