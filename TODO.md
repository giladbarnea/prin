# Issues and To-dos

- [ ] If nothing matches with the given filters, but would match if any include flag was specified, we should print a subtle hint that the user might want to use the include flags.
- [ ] README.md should have an example output early in the README, after the basic usage.
- [ ] README.md should have a website example.
- [ ] `-t`, `--tag` is a bad name. It should be `--format` or `--output-format`, or something with 'seperator'.
- [ ] Network requests cache TTL

## PARITIES.md

- [ ] Stronger symbol verification
  - [ ] AST-scan for module-level constants (ALL_CAPS) with module scoping
  - [ ] Argparse introspection via AST to extract flags/aliases/defaults and diff vs README and `defaults.py`

- [ ] Explainable results (LLM guidance)
  - [ ] Show first N file:line matches per token (cap N to keep output concise)

- [ ] Suppressions in PARITIES.md
  - [ ] Inline opt-outs with explicit tokens: `// noqa: <token[, token...]>`
