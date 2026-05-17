Feature: shame next snippet rendering
  shame next renders the suppression snippet from the registry's cached
  `content` field. The renderer must not open or display files referenced
  by `location`, so that a `location` pointing outside the repository
  (absolute path or `..` traversal) never discloses file contents.

  Scenario: Absolute location pointing outside the repository does not leak file contents
    Given a project with a hand-crafted shamefile.yaml
    And a sensitive file outside the project containing "SHOULD_NOT_LEAK_AAAA"
    And the registry has an entry whose location is the absolute path of that file at line 1
    When I run shame next
    Then the command exits with code 0
    And stdout does not contain "SHOULD_NOT_LEAK_AAAA"
    And stdout contains "placeholder"

  Scenario: Parent-dir traversal in location does not leak file contents
    Given a project with a hand-crafted shamefile.yaml
    And a sensitive file outside the project containing "OUTSIDE_REPO_BBBB"
    And the registry has an entry whose location is a "../"-prefixed path to that file at line 1
    When I run shame next
    Then the command exits with code 0
    And stdout does not contain "OUTSIDE_REPO_BBBB"
    And stdout contains "placeholder"

  Scenario: shame next with reason advances without leaking the next entry's target file
    Given a project with a hand-crafted shamefile.yaml
    And a sensitive file outside the project containing "CHAINED_LEAK_CCCC"
    And the registry has two undocumented entries: a benign one followed by an absolute path to that file at line 1
    When I run shame next with reason "benign fix"
    Then the command exits with code 0
    And stdout does not contain "CHAINED_LEAK_CCCC"
    And stdout contains "placeholder"

  Scenario: Legitimate entry renders snippet from registry content
    Given a project with a hand-crafted shamefile.yaml
    And the registry has an entry at "./code.py:42" with token "# noqa" and content "x = 1  # noqa"
    When I run shame next
    Then the command exits with code 0
    And stdout contains "./code.py:42"
    And stdout contains "x = 1  # noqa"
    And stdout contains "  42|"
