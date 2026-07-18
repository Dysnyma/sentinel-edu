## ADDED Requirements

### Requirement: Silent exception catch must include diagnostic output

The system SHALL NOT silently discard exceptions. Every `except Exception:` block MUST produce either a user-facing warning (in UI-layer code) or a console diagnostic message (in backend code) before falling through to the default/recovery value.

#### Scenario: Backend function exception when generating AI title

- **WHEN** `save_dataset()` calls `_generate_dataset_title()` and an exception is raised
- **THEN** the system SHALL print a warning message to the console with the exception context
- **AND** the function SHALL continue with the default title `'测试集'`

#### Scenario: Backend function exception when parsing metadata JSON

- **WHEN** `list_datasets()` reads a metadata file and `json.load()` raises an exception
- **THEN** the system SHALL print a warning message to the console with the file path and exception context
- **AND** the function SHALL continue with empty metadata defaults

#### Scenario: UI function exception when generating AI title suggestion

- **WHEN** `tab1_build.py` calls `_generate_dataset_title()` and an exception is raised
- **THEN** the system SHALL display a `st.warning()` message to the user
- **AND** the function SHALL continue with the default title

#### Scenario: UI function exception when inserting DB initial record

- **WHEN** `tab2_detect.py` inserts an initial DB record via `save_result()` and an exception is raised
- **THEN** the system SHALL display a `st.warning()` message to the user identifying the text_id
- **AND** the function SHALL continue processing remaining records
