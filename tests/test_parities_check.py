from internal.parities_check import (
    extract_ast_tokens_from_members,
    extract_constant_tokens_from_members,
    parse_parities,
)
import pytest
import os
import shutil
import subprocess


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

    # Should include only AST-resolvable symbol tokens, not files or wildcards
    assert tokens == [
        "parse_common_args",
        "Context",
        "_expand_cli_aliases",
        "DepthFirstPrinter._set_from_context",
    ]

    # File tokens should be captured separately and resolvable
    file_tokens = set_block.member_paths()
    for path in [
        "README.md",
        "src/prin/cli_common.py",
        "src/prin/defaults.py",
        "src/prin/core.py",
    ]:
        assert path in file_tokens


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

    # Assert subsections exist and contain bullets
    for section_name in ["Members", "Contract", "Triggers", "Tests"]:
        assert section_name in set_block.sections
        assert len(set_block.sections[section_name]) >= 1

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


def test_symbex_resolves_member_symbols():
    block = """
    ## Set 1 [CLI-CTX-DEFAULTs-README]: CLI options ↔ Context fields ↔ Defaults ↔ README
    **Members**
    - `README.md` (options and usage)
    - `src/prin/cli_common.py` (`parse_common_args(...)`, `Context` fields, `_expand_cli_aliases`)
    - `src/prin/defaults.py` (`DEFAULT_*` used by CLI defaults and choices)
    - `src/prin/core.py` (`DepthFirstPrinter._set_from_context` consumption/behavior tied to flags)
    """
    parsed = parse_parities(block)
    set_block = parsed.sets[1]
    tokens = extract_ast_tokens_from_members(set_block.members_text)
    # Keep only function/class symbols suitable for symbex; exclude paths and constants
    sym_tokens = [
        t for t in tokens if \
        t not in {"README.md", "DEFAULT_*"} and \
        "/" not in t
    ]

    # Determine how to invoke symbex
    symbex_cmd = None
    if shutil.which("symbex"):
        symbex_cmd = ["symbex"]
    elif shutil.which("uv"):
        symbex_cmd = ["uv", "run", "symbex"]
    else:
        # symbex not available; skip
        return

    env = os.environ.copy()
    # Prefer local .venv / uv toolchain if present
    home = os.path.expanduser("~")
    env["PATH"] = f"{home}/.local/bin:" + env.get("PATH", "")

    for symbol in sym_tokens:
        # Verify that symbex returns some output for each symbol
        proc = subprocess.run(
            [*symbex_cmd, "-d", "src", symbol, "-s"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        assert proc.returncode == 0
        assert symbol.split(".")[-1] in proc.stdout or proc.stdout.strip() != ""


def test_set2_sections_and_tokens_h3_h4_headings():
    block = """
    ## Set 2 [FORMATTER-SELECTION]: Tag choices ↔ Formatter classes ↔ Defaults ↔ README examples

    ### Members

    - `src/prin/prin.py` (tag→formatter dispatch)
    - `src/prin/formatters.py` (`XmlFormatter`, `MarkdownFormatter`, `HeaderFormatter`)
    - `src/prin/defaults.py` (`DEFAULT_TAG_CHOICES`)
    - `README.md` (output examples)

    #### Contract
    - Values in `DEFAULT_TAG_CHOICES` exactly match the dispatch table in `prin.py`, with a concrete formatter class for each value.
    - README examples reflect the actual output shape for each tag.

    #### Triggers
    - Adding a tag; changing a formatter’s behavior or format.

    ### Tests
    - `tests/test_options_fs.py::test_tag_md_outputs_markdown_format`
    - `tests/test_options_repo.py::test_repo_tag_md_outputs_markdown_format`
    """
    parsed = parse_parities(block)
    assert 2 in parsed.sets
    set_block = parsed.sets[2]
    assert set_block.sid == 2
    assert set_block.title.startswith("## Set 2 [FORMATTER-SELECTION]")

    # Subsection presence via h3/h4
    for section_name in ["Members", "Contract", "Triggers", "Tests"]:
        assert section_name in set_block.sections
        assert len(set_block.sections[section_name]) >= 1

    # Members: AST-resolvable tokens should include formatter classes (class tokens)
    ast_tokens = extract_ast_tokens_from_members(set_block.members_text)
    # Expected: XmlFormatter, MarkdownFormatter, HeaderFormatter
    for sym in ["XmlFormatter", "MarkdownFormatter", "HeaderFormatter"]:
        assert sym in ast_tokens
    # Constant-like tokens are verified separately
    const_tokens = extract_constant_tokens_from_members(set_block.members_text)
    assert "DEFAULT_TAG_CHOICES" in const_tokens
    # File tokens should be captured separately and resolvable
    file_tokens = set_block.member_paths()
    for path in [
        "src/prin/prin.py",
        "src/prin/formatters.py",
        "src/prin/defaults.py",
        "README.md",
    ]:
        assert path in file_tokens

    # Tests: verify test specs extraction
    test_specs = set_block.test_specs()
    assert ("tests/test_options_fs.py", "test_tag_md_outputs_markdown_format") in test_specs
    assert ("tests/test_options_repo.py", "test_repo_tag_md_outputs_markdown_format") in test_specs


def test_set3_only_headers_enforcement_members_contract_tests():
    block = """
    ## Set 3 [ONLY-HEADERS-ENFORCEMENT]: `--only-headers` flag ↔ HeaderFormatter behavior
    **Members**
    - `src/prin/cli_common.py` (`Context.only_headers` / CLI: `-l/--only-headers`)
    - `src/prin/core.py` (`DepthFirstPrinter` forcing `HeaderFormatter`)
    - `src/prin/formatters.py` (`HeaderFormatter`)

    **Contract**
    - When `only_headers` is true, body content must not be printed, regardless of selected formatter.

    **Triggers**
    - Changing `only_headers` semantics or formatter enforcement.

    **Tests**
    - FS: `tests/test_options_fs.py::test_only_headers_prints_headers_only`
    - Repo: `tests/test_options_repo.py::test_repo_only_headers_prints_headers_only`
    """
    parsed = parse_parities(block)
    assert 3 in parsed.sets
    set_block = parsed.sets[3]
    assert set_block.sid == 3
    assert set_block.title.startswith("## Set 3 [ONLY-HEADERS-ENFORCEMENT]")

    # Subsections exist and contain bullets
    for section_name in ["Members", "Contract", "Triggers", "Tests"]:
        assert section_name in set_block.sections
        assert len(set_block.sections[section_name]) >= 1

    # Members: AST-resolvable tokens include class attribute and class names
    ast_tokens = extract_ast_tokens_from_members(set_block.members_text)
    assert "Context.only_headers" in ast_tokens
    assert "DepthFirstPrinter" in ast_tokens
    assert "HeaderFormatter" in ast_tokens

    # Member file paths are captured
    file_tokens = set_block.member_paths()
    for path in [
        "src/prin/cli_common.py",
        "src/prin/core.py",
        "src/prin/formatters.py",
    ]:
        assert path in file_tokens

    # Contract tokens include the standalone reference (debated for verification)
    contract_tokens = set_block.backtick_tokens_in_sections(["Contract"])
    assert "only_headers" in contract_tokens

    # Tests include both FS and Repo checks
    test_specs = set_block.test_specs()
    assert ("tests/test_options_fs.py", "test_only_headers_prints_headers_only") in test_specs
    assert ("tests/test_options_repo.py", "test_repo_only_headers_prints_headers_only") in test_specs


def test_cli_flag_pair_extraction_all_forms():
    # Construct a block with a Tests section containing all 16 variants
    variants = [
        "-f/--foo-bar",
        "-f,--foo-bar",
        "-f / --foo-bar",
        "-f, --foo-bar",
        "`-f`/`--foo-bar`",
        "`-f` / `--foo-bar`",
        "`-f`,`--foo-bar`",
        "`-f`, `--foo-bar`",
    ]
    paren_variants = [f"({v})" for v in variants]
    lines = "\n".join(f"- {v}" for v in (variants + paren_variants))
    block = f"""
    ## Set 99 [FLAGS-TEST]: CLI flag extraction forms
    **Members**
    - `README.md`

    **Tests**
{lines}
    """
    block = block.format(lines=lines)
    parsed = parse_parities(block)
    set_block = parsed.sets[99]
    flags = set_block.cli_flags_in_tests()
    # Both flags should be captured
    assert flags.count("-f") >= 1
    assert flags.count("--foo-bar") >= 1
    assert "-f" in flags and "--foo-bar" in flags


def test_members_categorization_cli_flags_and_pytest_specs():
    block = """
    ## Set 100 [CATEGORIZE]: Token categorization in Members
    **Members**
    - `src/prin/core.py` (`-l/--only-headers`, `tests/test_options_fs.py::test_only_headers_prints_headers_only`)
    - `tests/test_options_repo.py::test_repo_only_headers_prints_headers_only`
    - `-x`/`--example-flag`
    """
    parsed = parse_parities(block)
    sb = parsed.sets[100]
    # Paths should include real files, not flags or pytest specs
    paths = sb.member_paths()
    assert "src/prin/core.py" in paths
    assert not any(p.startswith("-") for p in paths)
    assert not any("::" in p for p in paths)
    # Flags should be captured across all sections
    flags = sb.cli_flags_all_sections()
    assert "-l" in flags and "--only-headers" in flags and "-x" in flags and "--example-flag" in flags
    # Pytest specs captured across all sections
    specs = sb.pytest_specs_all_sections()
    assert ("tests/test_options_fs.py", "test_only_headers_prints_headers_only") in specs
    assert ("tests/test_options_repo.py", "test_repo_only_headers_prints_headers_only") in specs


@pytest.mark.parametrize(
    "id_a,id_b,should_warn",
    [
        ("[Alpha-Beta-Gamma]", "[alpha-Delta-Epsilon]", False),  # 1 shared part (alpha) only
        ("[CLI-CTX-DEFAULTs-README]", "[readme-defaults-core]", True),  # 2 shared parts, mixed case/order
        ("[FORMATTER-SELECTION-README]", "[readme-selection-formatter]", True),  # 3 shared parts, different order/case
    ],
)
def test_merge_opportunity_id_parts_only(id_a, id_b, should_warn, capsys):
    block = f"""
    ## Set 10 {id_a}: A
    **Members**
    - `README.md`

    ## Set 11 {id_b}: B
    **Members**
    - `README.md`
    """
    parsed = parse_parities(block)
    from internal.parities_check import rule_merge_opportunities

    msgs = rule_merge_opportunities(parsed)
    warn = any(m.severity == "WARN" and m.rule == "MergeOpportunity" for m in msgs)
    assert warn is should_warn