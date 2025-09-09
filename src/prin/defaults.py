# sudo fd -H -I '.*' -t f / --format "{/}" | awk -F. '/\./ && index($0,".")!=1 {ext=tolower($NF); if (length(ext) <= 10 && ext ~ /[a-z]/ && ext ~ /^[a-z0-9]+$/) print ext}' > /tmp/exts.txt  # For all file names which have a name and an extension, write to file lowercased extensions which are alphanumeric, <= 10 characters long, and have at least one letter
# rg --type-list | py.eval "[print(extension) for line in lines for ext in line.split(': ')[1].split(', ') if (extension:=ext.removeprefix('*.').removeprefix('.*').removeprefix('.').removeprefix('*').lower()).isalnum()]" --readlines >> /tmp/exts.txt
# sort -u -o /tmp/exts.txt /tmp/exts.txt

# OR:
# prin https://github.com/torvalds/linux -l --include-empty | tee /tmp/linux-tree.txt | { typeset -A seen; while IFS= read -r p; do b=${p##*/}; [[ $b = ?*.* ]] || continue; e=${b##*.}; [[ -z $seen[$e] ]] && { print -- $p; seen[$e]=1 };done ; }

# region ---[ Default Paths and Exclusions ]---

from typing import Literal, LiteralString

from prin.types import TExclusion

Hidden = lambda x: x.startswith(".")  # pyright: ignore[reportUnknownLambdaType]
"""Covers .env, .idea, and all dot-dirs and dot-files."""
HasCacheSubstr = lambda x: "cache" in str(x).lower()  # pyright: ignore[reportUnknownLambdaType]

DEFAULT_EXCLUSIONS: list[TExclusion] = [
    lambda x: x.endswith("egg-info"),
    "build",
    "bin",
    "dist",
    "node_modules",
    HasCacheSubstr,
    # Build artifacts and dependencies
    "target",
    "vendor",
    "out",
    "coverage",
    # Additional common directories/files
    "venv",
    "DerivedData",
    "Pods",
    "Carthage/Build",
    "coverage.out",
    # Logs and temporary files
    "logs",
    "*.log",
    "*.tmp",
    # Environment and secrets
    "secrets",
    "*.key",
    "*.pem",
]


DEFAULT_DOC_EXTENSIONS: list[str] = ["*.md", "*.rst", "*.mdx"]


DEFAULT_TEST_EXCLUSIONS: list[TExclusion] = [
    "*.test",
    "tests/*", # This should work but doesn't
    "tests*",  # This is a workaround that should be removed once the above works
    "test/*",
    "*.spec.ts",
    "*.spec.ts*",
    "*.test.ts",
    "*.test.ts*",
    "test_*",
]


DEFAULT_LOCK_EXCLUSIONS: list[TExclusion] = [
    "*.lock",
    # JavaScript/Node
    "package-lock.json",
    "pnpm-lock.yaml",
    "go.sum",
    "bun.lockb",
    "Package.resolved",
    "gradle.lockfile",
    "packages.lock.json",
]


DEFAULT_BINARY_EXCLUSIONS: list[TExclusion] = [
    # Binary files
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.exe",
    "*.dll",
    "*.app",
    "*.deb",
    "*.rpm",
    "*.dot",
    # Archives
    "*.zip",
    "*.tar",
    "*.gz",
    "*.bz2",
    "*.xz",
    "*.7z",
    "*.rar",
    "*.jar",
    "*.war",
    "*.ear",
    # Media files
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.bmp",
    "*.ico",
    "*.svg",
    "*.mp3",
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.wav",
    "*.pdf",  # TODO: Remove this when we support PDFs
    # Database and data files
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.dat",
    "*.bin",
    # IDE and editor files
    "*.swp",
    "*.swo",
    # Language-specific
    "*.class",
    "*.o",
    "*.so",
    "*.dylib",
    # Additional binary formats
    "*.node",
    "*.wasm",
    "*.zst",
    "*.lz",
    # Fonts
    "*.ttf",
    "*.otf",
    "*.woff",
    "*.woff2",
    "*.eot",
    # Windows build outputs
    "*.obj",
    "*.lib",
    "*.pdb",
    "*.ilk",
    # Installers/bundles
    "*.dmg",
    "*.pkg",
    "*.msi",
    "*.apk",
    "*.ipa",
    # Scientific/data formats
    "*.h5",
    "*.hdf5",
    "*.npz",
    "*.npy",
    "*.mat",
    "*.parquet",
    "*.feather",
    "*.arrow",
]

# endregion ---[ Default Paths and Exclusions ]---
# region ---[ Default CLI Options ]---

DEFAULT_RUN_PATH = "."
DEFAULT_INCLUDE_TESTS = False
DEFAULT_INCLUDE_LOCK = False
DEFAULT_INCLUDE_BINARY = False
DEFAULT_NO_DOCS = False
DEFAULT_INCLUDE_EMPTY = False
DEFAULT_ONLY_HEADERS = False
DEFAULT_EXTENSIONS_FILTER = []
DEFAULT_EXCLUDE_FILTER = []
DEFAULT_NO_EXCLUDE = False
DEFAULT_NO_IGNORE = False
DEFAULT_INCLUDE_HIDDEN = False

# Output format tag defaults
DEFAULT_TAG: LiteralString = "xml"
DEFAULT_TAG_CHOICES: Literal["xml", "md"] = [DEFAULT_TAG, "md"]

# endregion ---[ Default CLI Options ]---
