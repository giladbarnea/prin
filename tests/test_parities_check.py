from internal.parities_check import extract_ast_tokens_from_members, parse_parities


def test_block_members_tokens():
    block = """
    ## Set 1 [CLI-CTX-DEFAULTs-README]: CLI options ↔ Context fields ↔ Defaults ↔ README
    **Members**
    - `README.md` (options and usage)
    - `src/prin/cli_common.py` (`parse_common_args(...)`, `Context` fields, `_expand_cli_aliases`)
    - `src/prin/defaults.py` (`DEFAULT_*` used by CLI defaults and choices)
    - `src/prin/core.py` (`DepthFirstPrinter._set_from_context` consumption/behavior tied to flags)
    """
    parsed = parse_parities(block)
    assert 1 in parsed.sets
    set_block = parsed.sets[1]
    assert set_block.sid == 1
    # Verify Set title token matches fully without regex manipulation
    assert set_block.title == "## Set 1 [CLI-CTX-DEFAULTs-README]: CLI options ↔ Context fields ↔ Defaults ↔ README"

    tokens = extract_ast_tokens_from_members(set_block.members_text)

    assert tokens == [
        "README.md",
        "src/prin/cli_common.py",
        "parse_common_args",
        "Context",
        "_expand_cli_aliases",
        "src/prin/defaults.py",
        "DEFAULT_*",
        "src/prin/core.py",
        "DepthFirstPrinter._set_from_context",
    ]


def test_first_set_contract_triggers_tests_tokens():
    block = """
    ## Set 1 [CLI-CTX-DEFAULTs-README]: CLI options ↔ Context fields ↔ Defaults ↔ README
    **Members**
    - `README.md` (options and usage)
    - `src/prin/cli_common.py` (`parse_common_args(...)`, `Context` fields, `_expand_cli_aliases`)
    - `src/prin/defaults.py` (`DEFAULT_*` used by CLI defaults and choices)
    - `src/prin/core.py` (`DepthFirstPrinter._set_from_context` consumption/behavior tied to flags)

    **Contract**
    - Categories defined in `defaults.py` are described in `README`, and `fs_root` includes representative files for coverage. Category changes update all three.

    **Triggers**
    - Adding/removing/renaming a category; changing category semantics.

    **Tests**
    - FS flags: `tests/test_options_fs.py` (e.g., `--hidden`, `--include-tests`, `--include-lock`, `--include-binary`, `--no-docs`, `--include-empty`, `--exclude`, `--no-exclude`, `--extension`)
    - Repo analogs: `tests/test_options_repo.py`
    """
    parsed = parse_parities(block)
    set_block = parsed.sets[1]

    # README token without extension should be captured as 'README' from Contract line
    contract_tokens = set_block.backtick_tokens_in_sections(["Contract"])
    assert "defaults.py" in contract_tokens
    assert "README" in contract_tokens  # README with no extension
    assert "fs_root" in contract_tokens

    # Triggers have no backticked tokens
    triggers_tokens = set_block.backtick_tokens_in_sections(["Triggers"])
    assert triggers_tokens == []

    # Tests: capture test file paths
    test_specs = set_block.test_specs()
    assert ("tests/test_options_fs.py", None) in test_specs
    assert ("tests/test_options_repo.py", None) in test_specs

    # And capture CLI flags separately for future symbex verification
    flags = set_block.cli_flags_in_tests()
    assert flags == [
        "--hidden",
        "--include-tests",
        "--include-lock",
        "--include-binary",
        "--no-docs",
        "--include-empty",
        "--exclude",
        "--no-exclude",
        "--extension",
    ]