Feature: YAML formatting of why field
  shamefile.yaml must store why values correctly regardless of
  how the user provides them — via CLI or manual edit.

  After `shame me`, every non-empty why is stored in one of two canonical formats:

    - single-quoted scalar when the resulting line fits within 80 characters:
          why: 'short reason'

    - folded block scalar (>-) when the line would exceed 80 characters,
      wrapped so no line exceeds 80 characters:
          why: >-
            first line of the reason
            continuation on the next line

  Any other YAML form the user writes (plain scalar, double-quoted, |, ~, Null,
  TRUE, numbers, tagged values, etc.) is normalized to one of these two formats
  on the next `shame me` run. Empty or null values are treated as undocumented.

  # --- Via CLI (shame next) ---

  Scenario: Short reason stays on one line
    Given a project with one suppression
    When I run shame next with reason:
      """
      Legacy code
      """
    Then shamefile.yaml contains entry with:
      """
      why: 'Legacy code'
      """

  Scenario: Reason with apostrophe is properly quoted
    Given a project with one suppression
    When I run shame next with reason:
      """
      Can't narrow type
      """
    Then shamefile.yaml contains entry with:
      """
      why: 'Can''t narrow type'
      """

  Scenario: Reason with colon and hash is preserved
    Given a project with one suppression
    When I run shame next with reason:
      """
      TODO: remove after v2.0 release # tracked in sprint 42
      """
    Then shamefile.yaml contains entry with:
      """
      why: 'TODO: remove after v2.0 release # tracked in sprint 42'
      """

  Scenario: Reason with URL longer than 80 chars is folded
    Given a project with one suppression
    When I run shame next with reason:
      """
      Line exceeds limit due to URL: https://api.example.com/v1/very/long/endpoint/path
      """
    Then no line in shamefile.yaml exceeds 80 characters
    And shamefile.yaml contains entry with:
      """
      why: >-
        Line exceeds limit due to URL:
        https://api.example.com/v1/very/long/endpoint/path
      """

  Scenario: Reason with double quotes is preserved
    Given a project with one suppression
    When I run shame next with reason:
      """
      Third-party lib returns "Any" type
      """
    Then shamefile.yaml contains entry with:
      """
      why: 'Third-party lib returns "Any" type'
      """

  Scenario: Reason with percent sign is preserved
    Given a project with one suppression
    When I run shame next with reason:
      """
      100% coverage not needed for this branch
      """
    Then shamefile.yaml contains entry with:
      """
      why: '100% coverage not needed for this branch'
      """

  Scenario: Reason with emoji is preserved
    Given a project with one suppression
    When I run shame next with reason:
      """
      Suppression needed for legacy migration 🔥
      """
    Then shamefile.yaml contains entry with:
      """
      why: 'Suppression needed for legacy migration 🔥'
      """

  Scenario: Reason in non-latin script is preserved
    Given a project with one suppression
    When I run shame next with reason:
      """
      日本語の理由
      """
    Then shamefile.yaml contains entry with:
      """
      why: '日本語の理由'
      """

  Scenario: Reason with YAML-like content is stored as string
    Given a project with one suppression
    When I run shame next with reason:
      """
      yaml: {nested: value}
      """
    Then shamefile.yaml contains entry with:
      """
      why: 'yaml: {nested: value}'
      """

  Scenario: Reason with YAML keyword "null" is stored as string
    Given a project with one suppression
    When I run shame next with reason:
      """
      null
      """
    Then shamefile.yaml contains entry with:
      """
      why: 'null'
      """

  Scenario: Reason with YAML keyword "true" is stored as string
    Given a project with one suppression
    When I run shame next with reason:
      """
      true
      """
    Then shamefile.yaml contains entry with:
      """
      why: 'true'
      """

  Scenario: Reason with number is stored as string
    Given a project with one suppression
    When I run shame next with reason:
      """
      42
      """
    Then shamefile.yaml contains entry with:
      """
      why: '42'
      """

  Scenario: Long reason is folded to >- so no line exceeds 80 characters
    Given a project with one suppression
    When I run shame next with reason:
      """
      Decorator returns HttpRequest (Django base), not HttpReq which declares auth UserMetadata. Mypy does not see authorize on the base type. This is a known issue since Django 4.0 and it cannot be fixed without coupling the generic decorator to a domain-specific subclass which entirely breaks the reusability.
      """
    Then no line in shamefile.yaml exceeds 80 characters
    And shamefile.yaml contains entry with:
      """
      why: >-
            Decorator returns HttpRequest (Django base), not HttpReq which declares
            auth UserMetadata. Mypy does not see authorize on the base type. This is a
            known issue since Django 4.0 and it cannot be fixed without coupling the
            generic decorator to a domain-specific subclass which entirely breaks the
            reusability.
      """

  Scenario: Long reason with special chars is folded and round-trips
    Given a project with one suppression
    When I run shame next with reason:
      """
      Decorator returns HttpRequest (Django base), not HttpReq which declares auth: UserMetadata. Mypy doesn't see .authorize() on the base type. # This is a known issue since Django 4.0. Can't use narrowing here because it would couple the generic decorator to a domain-specific subclass and break the reusability pattern we've established.
      """
    Then no line in shamefile.yaml exceeds 80 characters
    And shamefile.yaml contains entry with:
      """
      why: >-
            Decorator returns HttpRequest (Django base), not HttpReq which declares
            auth: UserMetadata. Mypy doesn't see .authorize() on the base type. # This
            is a known issue since Django 4.0. Can't use narrowing here because it
            would couple the generic decorator to a domain-specific subclass and break
            the reusability pattern we've established.
      """

  # --- Via manual edit ---

  Scenario: Manual edit with single-quoted value stays unchanged
    Given a project with one suppression and manual edit:
      """
      why: 'Legacy code'
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'Legacy code'
      """

  Scenario: Manual edit with single-quoted value containing colon stays unchanged
    Given a project with one suppression and manual edit:
      """
      why: 'reason: important context'
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'reason: important context'
      """

  Scenario: Manual edit with hash preserves full value
    Given a project with one suppression and manual edit:
      """
      why: see # TODO
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'see # TODO'
      """

  Scenario: Manual edit with apostrophe in plain scalar survives
    Given a project with one suppression and manual edit:
      """
      why: Can't narrow
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'Can''t narrow'
      """

  Scenario: Manual edit with null is treated as undocumented
    Given a project with one suppression and manual edit:
      """
      why: null
      """
    When I run shame me
    Then shame me exits with code 1
    And shamefile.yaml contains entry with:
      """
      why: ''
      """

  Scenario: Manual edit with true is normalized to quoted string
    Given a project with one suppression and manual edit:
      """
      why: true
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'true'
      """

  Scenario: Manual edit with number is normalized to quoted string
    Given a project with one suppression and manual edit:
      """
      why: 42
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: '42'
      """

  Scenario: Manual edit with unquoted colon is normalized to single-quoted string
    Given a project with one suppression and manual edit:
      """
      why: reason: important
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'reason: important'
      """

  Scenario: Manual edit with literal block scalar | is normalized to single-line
    Given a project with one suppression and manual edit:
      """
      why: |
          This is a long explanation
          spanning multiple lines
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'This is a long explanation spanning multiple lines'
      """

  Scenario: Manual edit with folded block scalar >- is normalized to single-line
    Given a project with one suppression and manual edit:
      """
      why: >-
          This is a long explanation
          spanning multiple lines
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'This is a long explanation spanning multiple lines'
      """

  Scenario: Long manual-edited reason with escaped apostrophes is folded
    Given a project with one suppression and manual edit:
      """
      why: 'Decorator returns HttpRequest (Django base), not HttpReq which declares auth: UserMetadata. Mypy does not see .authorize() on the base type. # This is a known issue since Django 4.0. Can''t use ''narrowing'' here because it would couple the generic decorator to a domain-specific subclass and break the reusability pattern we established in the auth module.'
      """
    When I run shame me
    Then shame me exits with code 0
    And no line in shamefile.yaml exceeds 80 characters
    And shamefile.yaml contains entry with:
      """
      why: >-
            Decorator returns HttpRequest (Django base), not HttpReq which declares
            auth: UserMetadata. Mypy does not see .authorize() on the base type. #
            This is a known issue since Django 4.0. Can't use 'narrowing' here because
            it would couple the generic decorator to a domain-specific subclass and
            break the reusability pattern we established in the auth module.
      """

  Scenario: Manual edit with literal block scalar | containing colon is normalized
    Given a project with one suppression and manual edit:
      """
      why: |
          reason: important context
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'reason: important context'
      """

  Scenario: Manual edit with literal block scalar | containing hash is normalized
    Given a project with one suppression and manual edit:
      """
      why: |
          see # TODO
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'see # TODO'
      """

  Scenario: Manual edit with literal block scalar | containing apostrophe is normalized
    Given a project with one suppression and manual edit:
      """
      why: |
          Can't narrow type
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'Can''t narrow type'
      """

  Scenario: Manual edit with literal block scalar | containing "null" is normalized to string
    Given a project with one suppression and manual edit:
      """
      why: |
          null
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'null'
      """

  Scenario: Manual edit with literal block scalar | containing "true" is normalized to string
    Given a project with one suppression and manual edit:
      """
      why: |
          true
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'true'
      """

  Scenario: Manual edit with 300-character literal block scalar is folded
    Given a project with one suppression and manual edit:
      """
      why: |
          Decorator returns HttpRequest (Django base), not HttpReq which declares auth UserMetadata. Mypy does not see authorize on the base type. This is a known issue since Django 4.0 and it cannot be fixed without coupling the generic decorator to a domain-specific subclass which entirely breaks the reusability.
      """
    When I run shame me
    Then no line in shamefile.yaml exceeds 80 characters
    And shamefile.yaml contains entry with:
      """
      why: >-
            Decorator returns HttpRequest (Django base), not HttpReq which declares
            auth UserMetadata. Mypy does not see authorize on the base type. This is a
            known issue since Django 4.0 and it cannot be fixed without coupling the
            generic decorator to a domain-specific subclass which entirely breaks the
            reusability.
      """

  Scenario: Manual edit with folded block scalar preserves internal multi-spaces
    Given a project with one suppression and manual edit:
      """
      why: >-
          word1    word2
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'word1    word2'
      """

  Scenario: Manual edit with empty literal block scalar is treated as undocumented
    Given a project with one suppression and manual edit:
      """
      why: |
      """
    When I run shame me
    Then shame me exits with code 1
    And shamefile.yaml contains entry with:
      """
      why: ''
      """

  # --- YAML syntax edge cases ---

  Scenario: Manual edit with tilde (~) is treated as undocumented
    Given a project with one suppression and manual edit:
      """
      why: ~
      """
    When I run shame me
    Then shame me exits with code 1
    And shamefile.yaml contains entry with:
      """
      why: ''
      """

  Scenario: Manual edit with "Null" keyword is treated as undocumented
    Given a project with one suppression and manual edit:
      """
      why: Null
      """
    When I run shame me
    Then shame me exits with code 1
    And shamefile.yaml contains entry with:
      """
      why: ''
      """

  Scenario: Manual edit with "TRUE" is stored as string (YAML 1.2 case-sensitive)
    Given a project with one suppression and manual edit:
      """
      why: TRUE
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'TRUE'
      """

  Scenario: Manual edit with "FALSE" is stored as string (YAML 1.2 case-sensitive)
    Given a project with one suppression and manual edit:
      """
      why: FALSE
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'FALSE'
      """

  Scenario: Manual edit with ".inf" is stored as string
    Given a project with one suppression and manual edit:
      """
      why: .inf
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: '.inf'
      """

  Scenario: Manual edit with ".nan" is stored as string
    Given a project with one suppression and manual edit:
      """
      why: .nan
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: '.nan'
      """

  Scenario: Manual edit with plain scalar starting with dash is preserved
    Given a project with one suppression and manual edit:
      """
      why: -value
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: '-value'
      """

  Scenario: Manual edit with double-quoted scalar is normalized to single-quoted
    Given a project with one suppression and manual edit:
      """
      why: "double quoted"
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'double quoted'
      """

  Scenario: Manual edit with empty double-quoted string is treated as undocumented
    Given a project with one suppression and manual edit:
      """
      why: ""
      """
    When I run shame me
    Then shame me exits with code 1
    And shamefile.yaml contains entry with:
      """
      why: ''
      """

  Scenario: Manual edit with explicit string tag !!str is normalized
    Given a project with one suppression and manual edit:
      """
      why: !!str 42
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: '42'
      """

  Scenario: Manual edit with double-quoted escape sequence is normalized to single-line
    Given a project with one suppression and manual edit:
      """
      why: "line1\nline2"
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'line1 line2'
      """

  Scenario: Manual edit with leading spaces in single-quoted value is preserved
    Given a project with one suppression and manual edit:
      """
      why: '  leading spaces'
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: '  leading spaces'
      """

  Scenario: Manual edit with trailing spaces in single-quoted value is preserved
    Given a project with one suppression and manual edit:
      """
      why: 'trailing spaces  '
      """
    When I run shame me
    Then shamefile.yaml contains entry with:
      """
      why: 'trailing spaces  '
      """

  Scenario: Generated shamefile.yaml passes yamllint with default config
    Given a project with one suppression and manual edit:
      """
      why: 'Decorator returns HttpRequest (Django base), not HttpReq which declares auth UserMetadata. Mypy does not see authorize on the base type.'
      """
    When I run shame me
    Then shamefile.yaml passes yamllint with default config
    And no line in shamefile.yaml exceeds 80 characters
    And shamefile.yaml contains entry with:
      """
      why: >-
            Decorator returns HttpRequest (Django base), not HttpReq which declares
            auth UserMetadata. Mypy does not see authorize on the base type.
      """

  Scenario: Generated shamefile.yaml passes prettier with default config
    Given a project with one suppression and manual edit:
      """
      why: 'Decorator returns HttpRequest (Django base), not HttpReq which declares auth UserMetadata. Mypy does not see authorize on the base type.'
      """
    When I run shame me
    Then shamefile.yaml passes prettier with default config
