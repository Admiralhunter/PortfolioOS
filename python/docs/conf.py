"""Sphinx configuration for PortfolioOS analytics engine."""

import os
import sys

# Add the project root to sys.path so autodoc can find the package
sys.path.insert(0, os.path.abspath(".."))

# -- Project information ---

project = "PortfolioOS Analytics"
author = "PortfolioOS Contributors"
release = "0.1.0"

# -- General configuration ---

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]

# Napoleon settings (Google-style docstrings)
napoleon_google_docstrings = True
napoleon_numpy_docstrings = False
napoleon_include_init_with_doc = True

# Autodoc settings
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

# -- Options for HTML output ---

html_theme = "alabaster"

# -- Options for JSON output ---
# Used by: sphinx-build -b json docs .reports/docs/json

# Exclude patterns
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
