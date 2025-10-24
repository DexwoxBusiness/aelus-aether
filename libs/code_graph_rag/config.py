"""Configuration constants for code_graph_rag library."""

# Patterns to ignore when processing code repositories
IGNORE_PATTERNS = [
    # Version control
    ".git",
    ".svn",
    ".hg",
    # Dependencies
    "node_modules",
    "vendor",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    "*.pyc",
    # Build outputs
    "dist",
    "build",
    "target",
    "out",
    ".next",
    ".nuxt",
    # IDE
    ".idea",
    ".vscode",
    ".vs",
    "*.swp",
    "*.swo",
    # OS
    ".DS_Store",
    "Thumbs.db",
    # Test coverage
    "coverage",
    ".coverage",
    "htmlcov",
    ".pytest_cache",
    # Misc
    "*.min.js",
    "*.min.css",
    "*.map",
]
