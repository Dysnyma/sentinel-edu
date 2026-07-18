## ADDED Requirements

### Requirement: BBDown URL must pass domain whitelist before execution

The system SHALL validate that any URL passed to `download_bilibili_video()` belongs to an allowed domain before passing it to the BBDown subprocess. Only `bilibili.com` and `b23.tv` domains SHALL be permitted.

#### Scenario: Valid bilibili.com URL passes through

- **WHEN** a URL with domain `bilibili.com` (including subdomains like `www.bilibili.com`) is passed to `download_bilibili_video()`
- **THEN** the function SHALL proceed to call BBDown normally
- **AND** the URL validation SHALL NOT raise an error

#### Scenario: Valid b23.tv short URL passes through

- **WHEN** a URL with domain `b23.tv` is passed to `download_bilibili_video()`
- **THEN** the function SHALL proceed to call BBDown normally
- **AND** the URL validation SHALL NOT raise an error

#### Scenario: Invalid domain is rejected

- **WHEN** a URL with a domain outside the whitelist is passed to `download_bilibili_video()`
- **THEN** the function SHALL raise a `ValueError` with a user-friendly message
- **AND** the BBDown subprocess SHALL NOT be executed

#### Scenario: URL with no domain is rejected

- **WHEN** a string that is not a valid URL is passed to `download_bilibili_video()`
- **THEN** the function SHALL raise a `ValueError`
- **AND** the BBDown subprocess SHALL NOT be executed
