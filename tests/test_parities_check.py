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