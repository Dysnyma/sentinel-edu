## ADDED Requirements

### Requirement: Unused imports shall be removed

The codebase SHALL NOT contain `import` statements for modules or symbols that are not referenced elsewhere in the same file, with the explicit exception of `views/__init__.py` which serves as a public API facade.

#### Scenario: Unused import is detected and removed

- **WHEN** a file contains an `import` statement for a symbol that is never used in that file
- **THEN** the import statement SHALL be removed
- **AND** no other code in the file SHALL be modified

### Requirement: Assigned-but-unused variables shall be removed

The codebase SHALL NOT contain variable assignments whose value is never subsequently read.

#### Scenario: Assigned variable is never read

- **WHEN** a variable is assigned a value but never referenced again
- **THEN** the assignment statement SHALL be removed

### Requirement: Ambiguous variable names shall be renamed

Variable names that are visually ambiguous SHALL be renamed to descriptive alternatives.

#### Scenario: Single-letter `l` is used

- **WHEN** a variable named `l` appears in any context
- **THEN** it SHALL be renamed to `span` (or another descriptive name based on context)

### Requirement: Whitespace and formatting shall follow PEP 8

The codebase SHALL adhere to PEP 8 style conventions for whitespace around operators, blank lines before nested definitions, indentation, and spacing after commas.

#### Scenario: Formatting violations are detected

- **WHEN** a file has E226 (missing whitespace around operator), E306 (missing blank line before nested def), E128 (under-indented continuation line), or E231 (missing whitespace after comma) violations
- **THEN** each violation SHALL be corrected at the specific line
- **AND** no other formatting changes SHALL be made beyond the specific violations listed
