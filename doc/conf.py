# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import importlib.metadata

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys

# sys.path.insert(0, os.path.abspath("../roseau/"))

# -- Project information -----------------------------------------------------

project = "Roseau Load Flow"
copyright = "2022, Roseau Technologies SAS"
# author = "Benoît Vinot"

# The full version, including alpha/beta/rc tags
version = importlib.metadata.version("roseau_load_flow")
release = f"{project} {version}"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.mathjax",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "nbsphinx",
    "autoapi.extension",
]

add_module_names = False
napoleon_numpy_docstring = False
nbsphinx_allow_errors = True
python_use_unqualified_type_names = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for autodoc ----------------------------------------------------
autodoc_default_options = {"ignore-module-all": False}
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autodoc_inherit_docstrings = True

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_show_copyright = True
html_title = f"{release}"
html_logo = "_static/Logo_Roseau_Technologies_Without_Baseline.png"
html_favicon = "_static/Favicon_Roseau_Technologies.ico"
html_theme_options = {
    "source_repository": "https://github.com/RoseauTechnologies/Roseau_Load_Flow/",
    # "source_branch": "main",
    # "source_directory": "source/",
    # "sidebar_hide_name": True,
    "navigation_with_keys": True,
    "light_css_variables": {
        "font-stack": "Poppins,Helvetica,Arial,Lucida,sans-serif",
        "color-announcement-background": "#222798"
        # "font-stack--monospace": "Courier, monospace",
    },
    "dark_css_variables": {
        "font-stack": "Poppins,Helvetica,Arial,Lucida,sans-serif",
        "color-announcement-background": "#222798"
        # "font-stack--monospace": "Courier, monospace",
    },
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Extra CSS files
html_css_files = ["css/custom.css"]

# -- Options for AutoAPI -------------------------------------------------
autoapi_dirs = ["../roseau"]
autoapi_ignore = ["**/tests/**", "**/conftest.py", "__about__.py"]
autoapi_options = ["members", "show-inheritance", "show-module-summary", "imported-members"]
autoapi_python_class_content = "both"  # without this, the __init__ docstring is not shown
autoapi_python_use_implicit_namespaces = True

# -- Options for intersphinx -------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "shapely": ("https://shapely.readthedocs.io/en/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "pint": ("https://pint.readthedocs.io/en/stable/", None),
}
