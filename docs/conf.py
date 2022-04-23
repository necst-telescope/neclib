import neclib


# -- Project information -----------------------------------------------------

project = "neclib"
copyright = "2022, NANTEN2 Software Team"
author = "NANTEN2 Software Team"
release = version = neclib.__version__

# -- General configuration ---------------------------------------------------

extensions = [
    "m2r2",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.graphviz",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autosummary_generate = True
add_module_names = False
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
autodoc_typehints = "description"
napoleon_use_ivar = True

# -- Options for HTML output -------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/nanten2/neclib",
            "icon": "fab fa-github-square",
            "type": "fontawesome",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/neclib/",
            "icon": "fas fa-cubes",
            "type": "fontawesome",
        },
    ],
    "navbar_start": ["navbar-logo"],
}
# html_logo = "_static/logo.svg"
html_favicon = "https://avatars.githubusercontent.com/u/20414019?s=400&u=0e47c7d5efc6cf27086c8cfcdb6fd5c757926043&v=4"  # noqa: E501
html_sidebars = {
    "**": [
        "version",
        "search-field.html",
        "sidebar-nav-bs.html",
    ],
}

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]


def summarize(app, what, name, obj, options, lines):
    import inspect

    def _get_attr(attrname):
        return getattr(obj, attrname, None)

    def _is_to_be_documented(attrname):
        if attrname.startswith("_"):
            return False
        attr = _get_attr(attrname)
        if attr is None:
            return False
        if inspect.ismodule(attr):
            return False
        module_name = getattr(attr, "__module__", "")
        if not module_name.startswith(project):
            return False
        if name == module_name:
            return False
        return True

    def _create_table(attr_names):
        ret = [".. csv-table::", "   :widths: auto", ""]
        for attr in attr_names:
            link = f":doc:`{attr} <{_get_attr(attr).__module__}>`"
            docs = getattr(_get_attr(attr), "__doc__", "").split("\n")[0]
            ret.append(f"   {link}, \"{docs}\"")
        return ret

    if what == "module":
        alias_names = [attr for attr in dir(obj) if _is_to_be_documented(attr)]
        if len(alias_names) > 0:
            lines.extend(["=======", "Aliases", "=======", ""])
            lines.extend(_create_table(alias_names))


def setup(app):
    app.connect("autodoc-process-docstring", summarize)
