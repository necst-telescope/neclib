# flake8: noqa

import os
import sys

try:
    from importlib_metadata import version
except ImportError:
    from importlib.metadata import version  # Python 3.8+

sys.path.insert(0, os.path.abspath("../necst_lib"))


# -- Project information -----------------------------------------------------

project = "necst_lib"
copyright = "2022, NANTEN2 Software Team"
author = "NANTEN2 Software Team"

# The full version, including alpha/beta/rc tags
try:
    release = version("necst_lib")
except:
    release = ""

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
    "github_url": "https://github.com/nanten2/necst-lib/",
}
# html_logo = "_static/logo.svg"
html_sidebars = {
    "**": [
        "sidebar-nav-bs.html",
        "sidebar-search-bs.html",
    ],
}

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
