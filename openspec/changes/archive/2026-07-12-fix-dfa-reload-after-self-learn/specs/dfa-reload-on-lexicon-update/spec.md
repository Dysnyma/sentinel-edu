## ADDED Requirements

### Requirement: DFA Scanner reloads when word list is updated via self-learning

The system SHALL ensure that after new sensitive words are appended to `sensitive_words.txt` through the self-learning workflow, the DFA Scanner's in-memory automaton reflects the updated word list without requiring an application restart.

#### Scenario: User adds words and immediately runs DFA scan

- **WHEN** the user confirms appending selected candidate words to `sensitive_words.txt` via the self-learning UI
- **THEN** the DFA Scanner SHALL be reloaded so that subsequent DFA scans within the same session detect the newly added words

#### Scenario: Reload confirmation is shown to the user

- **WHEN** words are successfully appended and the DFA Scanner is reloaded
- **THEN** the system SHALL display a confirmation message indicating the word list has been reloaded and is now effective

#### Scenario: No words added does not trigger reload

- **WHEN** the user attempts to append words but all selected words already exist in the word list (resulting in zero new words added)
- **THEN** the system SHALL NOT trigger a DFA Scanner reload, as the word list has not changed
