Feature: shame remove
  shame remove <location> <token> deletes a single entry from shamefile.yaml,
  identifying it by the same (location, token) pair used by shame fix.

  Together with shame next (read one) and shame fix (update one), shame remove
  closes the entry-level CRUD surface so humans and AI agents can delete an
  outdated entry without ever reading the full registry into context.

  Scenario: Removes the entry matching location and token
    Given a project with five suppressions
    When I run shame remove "./test.py:2" "# type: ignore"
    Then the command exits with code 0
    And stdout contains "Removed"
    And shamefile.yaml has 4 entries
    And shamefile.yaml does not contain token "# type: ignore"

  Scenario: Leaves other entries untouched
    Given a project with five suppressions
    When I run shame remove "./test.py:2" "# type: ignore"
    Then shamefile.yaml contains token "# noqa"
    And shamefile.yaml contains token "nosec"
    And shamefile.yaml contains token "# pragma: no cover"
    And shamefile.yaml contains token "# fmt: off"

  Scenario: Preserves why on other entries
    Given a project with five suppressions
    And the entry "./test.py:1" "# noqa" has why "kept reason"
    When I run shame remove "./test.py:2" "# type: ignore"
    Then the entry "./test.py:1" "# noqa" has why "kept reason"

  Scenario: Confirmation includes token and location
    Given a project with five suppressions
    When I run shame remove "./test.py:2" "# type: ignore"
    Then stdout contains "# type: ignore"
    And stdout contains "./test.py:2"

  Scenario: Wrong location fails with no-entry-found error
    Given a project with five suppressions
    When I run shame remove "./nonexistent.py:1" "# noqa"
    Then the command exits with code 1
    And stderr contains "No entry found"

  Scenario: Wrong token fails with no-entry-found error
    Given a project with five suppressions
    When I run shame remove "./test.py:1" "# type: ignore"
    Then the command exits with code 1
    And stderr contains "No entry found"

  Scenario: No-match leaves registry file unchanged
    Given a project with five suppressions
    And the registry contents are captured
    When I run shame remove "./nonexistent.py:1" "# noqa"
    Then the registry contents are unchanged

  Scenario: Missing token argument fails with clap usage error
    Given a project with five suppressions
    When I run shame remove "./test.py:1" without the token argument
    Then the command exits with code 2

  Scenario: Shows count of undocumented entries remaining
    Given a project with five suppressions
    When I run shame remove "./test.py:2" "# type: ignore"
    Then stdout contains "4 entries remaining"

  Scenario: Removing the only undocumented entry reports all documented
    Given a project with one undocumented suppression
    When I run shame remove "./test.py:1" "# noqa"
    Then the command exits with code 0
    And stdout contains "All entries documented"

  Scenario: Without registry fails with helpful message
    Given a project with no registry
    When I run shame remove "./test.py:1" "# noqa"
    Then the command exits with code 1
    And stderr contains "Registry not found"

  Scenario: rm is an alias for remove
    Given a project with five suppressions
    When I run shame rm "./test.py:2" "# type: ignore"
    Then the command exits with code 0
    And stdout contains "Removed"
    And shamefile.yaml has 4 entries
    And shamefile.yaml does not contain token "# type: ignore"
