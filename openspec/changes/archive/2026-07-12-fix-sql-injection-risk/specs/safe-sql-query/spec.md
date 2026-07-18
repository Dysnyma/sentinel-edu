## ADDED Requirements

### Requirement: Column name must be validated before SQL construction

The system SHALL ensure that any column name used in SQL string construction passes through a whitelist check before being embedded in the SQL statement.

#### Scenario: Whitelist column passes through

- **WHEN** `init_db()` iterates over the hardcoded column list `('llm_spans', 'llm_reason', 'dataset_id', 'text')`
- **THEN** each column name SHALL be checked against a whitelist set before being used in the `SELECT` statement
- **AND** the query SHALL execute normally with the validated column name

#### Scenario: Unknown column is rejected

- **WHEN** a column name outside the whitelist is passed to the SQL construction point
- **THEN** the system SHALL raise a `ValueError` and NOT execute the SQL statement
