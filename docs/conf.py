import os
import sys

sys.path.insert(0, os.path.abspath("../n_const"))


# -- Project information -----------------------------------------------------

project = "PACKAGENAME"
copyright = "2021, CREDIT"
author = "CREDIT"

# The full version, including alpha/beta/rc tags
release = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "m2r2",
]

templates_path = ["_templates"]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "github_url": "https://github.com/USERNAME/PACKAGENAME/",
}
html_logo = "_static/logo.svg"
html_sidebars = {
    "**": [
        "sidebar-nav-bs.html",
        "sidebar-search-bs.html",
    ],
}

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
