import re

from internal.parities_check import BACKTICK_TOKEN_RE, parse_parities

BLOCK = """
## Set 1 [CLI-CTX-DEFAULTs-README]: CLI options ↔ Context fields ↔ Defaults ↔ README
**Members**
- `README.md` (options and usage)
- `src/prin/cli_common.py` (`parse_common_args(...)`, `Context` fields, `_expand_cli_aliases`)
- `src/prin/defaults.py` (`DEFAULT_*` used by CLI defaults and choices)
- `src/prin/core.py` (`DepthFirstPrinter._set_from_context` consumption/behavior tied to flags)
"""


def test_block_members_tokens():
    parsed = parse_parities(BLOCK)
    assert 1 in parsed.sets
    set_block = parsed.sets[1]

    # Verify Set ID token from heading
    m = re.search(r"\[([^\]]+)\]", set_block.title)
    assert m is not None
    assert m.group(1) == "CLI-CTX-DEFAULTs-README"

    tokens = []
    for line in set_block.members_text:
        tokens.extend(BACKTICK_TOKEN_RE.findall(line))

    assert tokens == [
        "README.md",
        "src/prin/cli_common.py",
        "parse_common_args(...)",
        "Context",
        "_expand_cli_aliases",
        "src/prin/defaults.py",
        "DEFAULT_*",
        "src/prin/core.py",
        "DepthFirstPrinter._set_from_context",
    ]