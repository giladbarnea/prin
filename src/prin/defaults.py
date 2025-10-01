# sudo fd -H -I '.*' -t f / --format "{/}" | awk -F. '/\./ && index($0,".")!=1 {ext=tolower($NF); if (length(ext) <= 10 && ext ~ /[a-z]/ && ext ~ /^[a-z0-9]+$/) print ext}' > /tmp/exts.txt  # For all file names which have a name and an extension, write to file lowercased extensions which are alphanumeric, <= 10 characters long, and have at least one letter
# rg --type-list | py.eval "[print(extension) for line in lines for ext in line.split(': ')[1].split(', ') if (extension:=ext.removeprefix('*.').removeprefix('.*').removeprefix('.').removeprefix('*').lower()).isalnum()]" --readlines >> /tmp/exts.txt
# sort -u -o /tmp/exts.txt /tmp/exts.txt

# OR:
# prin https://github.com/torvalds/linux -l --include-empty | tee /tmp/linux-tree.txt | { typeset -A seen; while IFS= read -r p; do b=${p##*/}; [[ $b = ?*.* ]] || continue; e=${b##*.}; [[ -z $seen[$e] ]] && { print -- $p; seen[$e]=1 };done ; }

# region ---[ Default Paths and Exclusions ]---

import re
from typing import Literal

from prin.types import Glob, Pattern

Hidden = Glob(".*")
"""Covers .env, .idea, and all dot-dirs and dot-files."""

DEFAULT_EXCLUSIONS: list[Pattern] = [
    Glob("*egg-info"),
    re.compile(r"(^|/)build(/|$)"),
    re.compile(r"^bin(/|$)"),
    re.compile("dist"),
    re.compile("node_modules"),
    # Cache directories: only exclude path segments that END WITH 'cache' (case-insensitive),
    # e.g., '.ruff_cache', 'web_cache', 'Cache' — but do NOT exclude files like 'edge_cache.py'.
    re.compile(r"(^|/)[^/]*cache(/|$)", re.IGNORECASE),
    # Common special-case: Python bytecode caches
    re.compile(r"(^|/)__pycache__(/|$)"),
    # Build artifacts and dependencies
    re.compile("target"),
    re.compile("vendor"),
    re.compile("out"),
    re.compile("coverage"),
    # Additional common directories/files
    re.compile(r"(^|/)venv(/|$)"),
    # Minified assets
    Glob("*.min.*"),
    # Generated source artifacts (TypeScript, source maps)
    Glob("*.d.ts"),
    Glob("*.map"),
    # Version control artifacts
    Glob("*.orig"),
    Glob("*.rej"),
    # Editor backup files
    Glob("*.bak"),
    Glob("*.old"),
    # Additional editor temporary files
    Glob("*.swn"),  # Vim (complements .swp, .swo)
    Glob("*.temp"),
    # Language/IDE-specific generated files
    Glob("*.d"),  # C/C++ dependency files
    Glob("*.iml"),  # IntelliJ IDEA modules
    Glob("*.user"),  # Visual Studio user files (includes .csproj.user, .vbproj.user, etc.)
    re.compile("DerivedData"),
    re.compile("Pods"),
    re.compile(r"Carthage/Build"),
    re.compile(r"coverage\.out"),
    # Editor workspace and config files
    Glob("*.code-workspace"),  # VS Code/Cursor
    Glob("*.sublime-project"),  # Sublime Text
    Glob("*.sublime-workspace"),  # Sublime Text
    re.compile(r"Session\.vim"),  # Vim/Neovim
    re.compile(r"\.vim"),  # Vim
    re.compile(r"\.emacs\.d"),  # Emacs
    Glob("*~"),  # Emacs backup files
    # Logs and temporary files
    re.compile(r"logs", re.IGNORECASE),
    Glob("*.log"),
    Glob("*.tmp"),
    # Environment and secrets
    re.compile("secrets", re.IGNORECASE),
    Glob("*.key"),
    Glob("*.pem"),
]


DEFAULT_DOC_EXTENSIONS: list[Glob] = [Glob("*.md"), Glob("*.rst"), Glob("*.mdx"), Glob("*.1")]


DEFAULT_TEST_EXCLUSIONS: list[Pattern] = [
    re.compile(r".*\.test(\..+)?"),
    re.compile(r"tests?/"),
    re.compile(r"\.spec\.tsx?"),
    re.compile(r".test\.tsx?"),
    re.compile(r"/test_.*\.py.?"),
]


DEFAULT_LOCK_EXCLUSIONS: list[Pattern] = [
    Glob("*.lock"),
    Glob("*.lockfile"),
    # JavaScript/Node
    re.compile(r"package-lock\.json"),
    re.compile(r"pnpm-lock\.yaml"),
    re.compile(r"go\.sum"),
    re.compile(r"bun\.lockb"),
    re.compile(r"Package\.resolved"),
    re.compile(r"Cartfile\.resolved"),
    re.compile(r"packages\.lock\.json"),
]


DEFAULT_BINARY_EXCLUSIONS: list[Pattern] = [
    # Binary files
    Glob("*.pyc"),
    Glob("*.pyo"),
    Glob("*.pyd"),
    Glob("*.exe"),
    Glob("*.dll"),
    Glob("*.app"),
    Glob("*.deb"),
    Glob("*.rpm"),
    Glob("*.dot"),
    re.compile(r"bin/"),  # Dir
    # Archives
    Glob("*.zip"),
    Glob("*.tar"),
    Glob("*.gz"),
    Glob("*.bz2"),
    Glob("*.xz"),
    Glob("*.7z"),
    Glob("*.rar"),
    Glob("*.jar"),
    Glob("*.war"),
    Glob("*.ear"),
    # Media files
    Glob("*.png"),
    Glob("*.jpg"),
    Glob("*.jpeg"),
    Glob("*.gif"),
    Glob("*.bmp"),
    Glob("*.ico"),
    Glob("*.svg"),
    Glob("*.mp3"),
    Glob("*.mp4"),
    Glob("*.avi"),
    Glob("*.mov"),
    Glob("*.wav"),
    Glob("*.pdf"),  # TODO: Remove this when we support PDFs
    # Database and data files
    Glob("*.db"),
    Glob("*.sqlite"),
    Glob("*.sqlite3"),
    Glob("*.dat"),
    Glob("*.bin"),
    # IDE and editor files
    Glob("*.swp"),
    Glob("*.swo"),
    # Language-specific
    Glob("*.class"),
    Glob("*.o"),
    Glob("*.so"),
    Glob("*.dylib"),
    # Additional binary formats
    Glob("*.node"),
    Glob("*.wasm"),
    Glob("*.zst"),
    Glob("*.lz"),
    # Fonts
    Glob("*.ttf"),
    Glob("*.otf"),
    Glob("*.woff"),
    Glob("*.woff2"),
    Glob("*.eot"),
    # Windows build outputs
    Glob("*.obj"),
    Glob("*.lib"),
    Glob("*.pdb"),
    Glob("*.ilk"),
    # Installers/bundles
    Glob("*.dmg"),
    Glob("*.pkg"),
    Glob("*.msi"),
    Glob("*.apk"),
    Glob("*.ipa"),
    # Scientific/data formats
    Glob("*.h5"),
    Glob("*.hdf5"),
    Glob("*.npz"),
    Glob("*.npy"),
    Glob("*.mat"),
    Glob("*.parquet"),
    Glob("*.feather"),
    Glob("*.arrow"),
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
DEFAULT_TAG: Literal["xml"] = "xml"
DEFAULT_TAG_CHOICES: Literal["xml", "md"] = [DEFAULT_TAG, "md"]

# Depth control defaults
DEFAULT_MAX_DEPTH: int | None = None
DEFAULT_MIN_DEPTH: int | None = None
DEFAULT_EXACT_DEPTH: int | None = None

# endregion ---[ Default CLI Options ]---
