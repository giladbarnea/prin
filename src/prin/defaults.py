"""
The fact that the list types here are sometimes TExclusion and sometimes str is arbitrary and should carry no weight.
"""

# sudo fd -H -I '.*' -t f / --format "{/}" | awk -F. '/\./ && index($0,".")!=1 {ext=tolower($NF); if (length(ext) <= 10 && ext ~ /[a-z]/ && ext ~ /^[a-z0-9]+$/) print ext}' > /tmp/exts.txt  # For all file names which have a name and an extension, write to file lowercased extensions which are alphanumeric, <= 10 characters long, and have at least one letter
# rg --type-list | py.eval "[print(extension) for line in lines for ext in line.split(': ')[1].split(', ') if (extension:=ext.removeprefix('*.').removeprefix('.*').removeprefix('.').removeprefix('*').lower()).isalnum()]" --readlines >> /tmp/exts.txt
# sort -u -o /tmp/exts.txt /tmp/exts.txt

# region ---[ Default Paths and Exclusions ]---

from prin.types import TExclusion

HiddenFiles = lambda x: x.startswith(".")

DEFAULT_EXCLUSIONS: list[TExclusion] = [
    lambda x: x.endswith("egg-info"),
    "build",
    "bin",
    "dist",
    "node_modules",
    HiddenFiles,
    lambda x: "cache" in str(x).lower(),
    # Build artifacts and dependencies
    "target",
    "vendor",
    "out",
    "coverage",
    # IDE and editor files
    "*.swp",
    "*.swo",
    # Language-specific
    "*.class",
    "*.o",
    "*.so",
    "*.dylib",
    # Logs and temporary files
    "logs",
    "*.log",
    "*.tmp",
    # Environment and secrets
    "secrets",
    "*.key",
    "*.pem",
]


DEFAULT_SUPPORTED_EXTENSIONS: list[str] = [
    ".py",
    ".ts",
    ".tsx",
    ".json",
    ".json*",
    ".html",
    ".ini",
    ".toml",
    ".yaml",
    ".yml",
    ".sh",
    ".zsh",
]


DEFAULT_DOC_EXTENSIONS: list[str] = [".md", ".rst", ".mdx"]


DEFAULT_TEST_EXCLUSIONS: list[TExclusion] = [
    "tests",
    "test",
    "spec.ts",
    "spec.ts*",
    "test.ts",
    "test.ts*",
]


DEFAULT_LOCK_EXCLUSIONS: list[TExclusion] = [
    # Python
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    # JavaScript/Node
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    # Other languages
    "Gemfile.lock",
    "composer.lock",
    "Cargo.lock",
    "go.sum",
    "mix.lock",
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

# Output format tag defaults
DEFAULT_TAG = "xml"
DEFAULT_TAG_CHOICES = ["xml", "md"]

# endregion ---[ Default CLI Options ]---
