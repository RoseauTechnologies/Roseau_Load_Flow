# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../roseau/"))


# -- Project information -----------------------------------------------------

project = "Roseau Load Flow"
copyright = "2022, Benoît Vinot"
author = "Benoît Vinot"

# The full version, including alpha/beta/rc tags
release = "0.1.0"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx_rtd_theme", "nbsphinx", "autoapi.extension"]

napoleon_numpy_docstring = False
autodoc_default_options = {"ignore-module-all": False}
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
python_use_unqualified_type_names = True
add_module_names = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
html_show_copyright = True
html_logo = "_static/Logo_Roseau_Technologies_With_Baseline.png"
html_favicon = "_static/Favicon_Roseau_Technologies.ico"
html_theme_options = {
    "logo_only": False,
    "display_version": True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# AutoAPI
autoapi_dirs = ["../roseau"]
autoapi_ignore = ["**/tests/**", "**/conftest.py"]
autoapi_options = ["members", "undoc-members", "show-inheritance", "show-module-summary", "imported-members"]
