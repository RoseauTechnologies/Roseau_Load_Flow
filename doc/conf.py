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
import os
import sys

sys.path.insert(0, os.path.abspath("../roseau/"))

# -- Project information -----------------------------------------------------

project = "Roseau Load Flow"
copyright = "2022, Roseau Technologies SAS"
# author = "Benoît Vinot"

# The full version, including alpha/beta/rc tags
release = importlib.metadata.version("roseau_load_flow")

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.mathjax",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "nbsphinx",
    "autoapi.extension",
]

napoleon_numpy_docstring = False
autodoc_default_options = {"ignore-module-all": False}
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
python_use_unqualified_type_names = True
add_module_names = False

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

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_show_copyright = True
html_title = f"{release}"
html_logo = "_static/Logo_Roseau_Technologies_With_Baseline.png"
html_favicon = "_static/Favicon_Roseau_Technologies.ico"
html_theme_options = {
    # "source_repository": "https://github.com/RoseauTechnologies/SIRAO_Documentation/",
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

# AutoAPI
autoapi_dirs = ["../roseau"]
autoapi_ignore = ["**/tests/**", "**/conftest.py"]
autoapi_options = ["members", "undoc-members", "show-inheritance", "show-module-summary", "imported-members"]

# Extra CSS files
html_css_files = ["css/custom.css"]
