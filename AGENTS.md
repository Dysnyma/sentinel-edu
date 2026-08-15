# AGENTS.md

Sentinel-Edu: Streamlit app (Python) for classroom-content safety analysis via DFA keyword scanning + LLM semantic analysis. All code comments, UI text, and commit messages are in Chinese — follow suit.

## Run & verify

- Dev server: `venv/bin/streamlit run app.py` (or just `streamlit run app.py`). Streamlit listens on **port 9000** (`.streamlit/config.toml`), not 8501.
- Tests: `venv/bin/python -m pytest tests` from repo root (project has no pytest config; `tests/` has `__init__.py`).
- Run one test: `venv/bin/python -m pytest tests/test_llm_client.py -k test_name`.
- Lint: `venv/bin/flake8 core/ views/ app.py --max-line-length=120 --ignore=E501,W503`.
- `test/code_audit.sh` (singular `test/`) runs flake8 + bandit + pip-audit and writes `test/code_audit_report.md`.
- `bash merge_py.sh` regenerates `all_py_code.txt` (all Python concatenated for LLM context).

## Test suite gotchas (important)

- **`side_effect` is silently ignored.** `tests/conftest.py` defines its own minimal `mocker` fixture that shadows pytest-mock's and only supports `return_value=` — its `patch()` drops `side_effect`. Do not write tests that pass `side_effect=` to `mocker.patch`; use `return_value=`, patch the real attribute with a Mock, or use `monkeypatch`.
- 3 tests currently fail (pre-existing) precisely because they rely on `side_effect`: `test_build_controller.py::TestRunTextCorrection::test_all_succeed` / `test_partial_failures`, and `test_detect_controller.py::TestInlineDetect::test_llm_error`. Expect them to fail; don't "fix" them by changing production code.
- `conftest.py` auto-stubs Whisper (`core.asr`) and provides fake `openai`/`ahocorasick`/`json_repair` so tests run offline without model downloads.
- Real Whisper/LLM/ffmpeg/BBDown are never exercised by tests.

## Architecture

- `app.py` is the only Streamlit entry. `core/` = pure business logic (controllers: `build_controller.py`, `detect_controller.py`, `analysis_controller.py`, `learn_controller.py`), `views/` = Streamlit UI only (`tab1_build.py`…`tab4_learn.py` + `helpers.py`). Keep this separation: new logic goes in `core/`, views only call `st.*` and controllers.
- `core/state.py` `init_state()` is the single source of truth for `session_state` defaults. `core/config.py` owns persistence (`data/apiconfig.json`, `data/session_state.json`, `data/prompts.json`, `data/providers.json`) and `_default_prompts()`.
- **`normalize_base_url()`** in `core/config.py` is the canonical base-URL normalizer (appends `/v1`). Always use it; don't re-implement inline `strip()/rstrip('/')/endswith('/v1')`.
- **`BaseLLMClient.get_instance(api_key, base_url, model)`** in `core/llm_client.py` is the only way to get an LLM client — it caches instances keyed by (key, base_url, model). Never `openai.OpenAI(...)` directly. Use `call()` (returns text) or `call_and_parse()` (returns `dict` via `json_repair`).
- DFA lexicon is `sensitive_words.txt` (one word per line, at repo root). `DFAScanner` must be `reload()`ed after lexicon changes.
- SQLite (`data/scan_results.db`) uses WAL mode + column-name whitelist; don't bypass the whitelist when building SQL.

## Data & secrets

- `data/` is gitignored except `data/providers.json` and `.gitkeep`. API keys, prompts, session state, and DB are runtime data — never commit them.
- LLM API config (key/base_url/model) lives in `data/apiconfig.json`, written automatically; do not log or print the API key.
- External tools: ffmpeg (required) and `./BBDown` (Bilibili downloader, gitignored binary at repo root).

## Workflow conventions

- This repo uses the **OpenSpec** change workflow: `openspec/` dir with `changes/` (proposal/design/tasks/specs per change), driven by Claude skills and slash commands under `.claude/` (`opsx:propose/apply/update/sync/archive`). When asked to plan a change, route it through this workflow rather than coding directly.
- Commit messages use Chinese conventional-commit prefixes (e.g. `fix:`, `feat:`, `refactor:`, `chore:`).
