"""Configuration Sphinx de la documentation MauriPay-Analytics."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"

sys.path.insert(0, str(BACKEND_SRC))

project = "MauriPay-Analytics"
author = "MauriPay Analytics Team"
copyright = "2026, MauriPay Analytics Team"
release = "0.2.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
master_doc = "index"
language = "fr"
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

autodoc_typehints = "description"

# Ces services ne sont accessibles que lorsque le backend et le frontend
# locaux sont demarres. Ils restent affiches dans la documentation, mais ne
# doivent pas faire echouer le controle automatique des liens externes.
linkcheck_ignore = [
    r"http://127\.0\.0\.1:8000(?:/.*)?",
    r"http://localhost:5173(?:/.*)?",
]
