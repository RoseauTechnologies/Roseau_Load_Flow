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
# import os
# import sys

# sys.path.insert(0, os.path.abspath("../roseau/"))

# -- Project information -----------------------------------------------------
project = "Roseau Load Flow"
copyright = "2018, Roseau Technologies SAS"
# author = "Benoît Vinot"

# The full version, including alpha/beta/rc tags
version = "0.11"
release = "0.11.0"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "autoapi.extension",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinxcontrib.googleanalytics",
    "sphinxcontrib.bibtex",
    "sphinx_sitemap",
    "sphinxext.opengraph",
]
myst_enable_extensions = ["deflist", "smartquotes", "replacements", "dollarmath"]
myst_html_meta = {"robots": "all"}
add_module_names = False
napoleon_numpy_docstring = False
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
exclude_patterns = ["images/*"]

# A list of paths that contain extra files not directly related to the documentation, such as robots.txt or .htaccess.
# Relative paths are taken as relative to the configuration directory. They are copied to the output directory.
# They will overwrite any existing file of the same name.
# As these files are not meant to be built, they are automatically excluded from source files.
html_extra_path = ["robots.txt", ".htaccess"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_show_copyright = True
html_title = f"{project} {release}"
html_logo = "_static/Roseau_Load_Flow_Stacked.svg"
html_favicon = "_static/Favicon_Roseau_Technologies.ico"
html_theme_options = {
    "source_repository": "https://github.com/RoseauTechnologies/Roseau_Load_Flow/",
    "source_branch": "main",
    "source_directory": "doc/",
    # "sidebar_hide_name": True,
    "navigation_with_keys": True,
    "light_css_variables": {"color-announcement-background": "#222798"},
    "dark_css_variables": {"color-announcement-background": "#222798"},
    "footer_icons": [
        {
            "name": "LinkedIn",
            "url": "https://www.linkedin.com/company/roseau-technologies/",
            "html": "",
            "class": "fa-brands fa-linkedin fa-2x",
        },
        {
            "name": "GitHub",
            "url": "https://github.com/RoseauTechnologies/",
            "html": "",
            "class": "fa-brands fa-github fa-2x",
        },
    ],
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Extra CSS files
html_css_files = ["css/custom.css"]

# Custom roles
rst_prolog = """
.. role:: roseau-primary
.. role:: roseau-secondary
.. role:: roseau-tertiary
"""


# -- Options for autodoc ----------------------------------------------------
autodoc_default_options = {"ignore-module-all": False}
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autodoc_inherit_docstrings = True
autoclass_content = "both"  # show both class and __init__ docstrings
autodoc_mock_imports = ["roseau.load_flow_engine"]  # Ignore missing dependencies when building the documentation


# -- Options for AutoAPI -------------------------------------------------
autoapi_dirs = ["../roseau"]
autoapi_ignore = ["**/tests/**", "**/conftest.py", "__about__.py"]
autoapi_options = ["members", "show-inheritance", "show-module-summary", "imported-members"]
autoapi_python_class_content = "both"  # without this, the __init__ docstring is not shown
autoapi_python_use_implicit_namespaces = True
suppress_warnings = ["autoapi.python_import_resolution"]  # For the import of roseau.load_flow_engine.cy_engine

# -- Options for intersphinx -------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "shapely": ("https://shapely.readthedocs.io/en/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
    "pint": ("https://pint.readthedocs.io/en/stable/", None),
    "typing_extensions": ("https://typing-extensions.readthedocs.io/en/stable/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "networkx": ("https://networkx.org/documentation/stable/", None),
    "pyproj": ("https://pyproj4.github.io/pyproj/stable/", None),
    "certifi": ("https://certifiio.readthedocs.io/en/latest/", None),
    "platformdirs": ("https://platformdirs.readthedocs.io/en/latest/", None),
}

# -- Options for sphinx_copybutton -------------------------------------------
copybutton_exclude = ".linenos, .gp, .go"
copybutton_copy_empty_lines = False
# https://sphinx-copybutton.readthedocs.io/en/latest/use.html#strip-and-configure-input-prompts-for-code-cells
copybutton_prompt_text = r">>> |\.\.\. |\$ |C:> |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# -- Options for sphinxcontrib.googleanalytics -------------------------------
googleanalytics_id = "G-Y9QSN78RFV"

# -- Options for sphinxcontrib.bibtex ----------------------------------------
bibtex_bibfiles = ["Bibliography.bib"]

# -- Options for sphinx.ext.extlinks -----------------------------------------
extlinks = {
    "gh-issue": ("https://github.com/RoseauTechnologies/Roseau_Load_Flow/issues/%s", "GH%s"),
    "gh-pr": ("https://github.com/RoseauTechnologies/Roseau_Load_Flow/pull/%s", "PR%s"),
}


# -- Options for sphinx-sitemap -----------------------------------------
html_baseurl = "https://roseau-load-flow.roseautechnologies.com/"
sitemap_url_scheme = "{link}"  # default is {lang}{version}{link}

# -- Options for sphinx-opengraph -----------------------------------------
ogp_site_url = "https://roseau-load-flow.roseautechnologies.com/"
ogp_image = "https://roseau-load-flow.roseautechnologies.com/_static/Roseau_Load_Flow_Stacked.svg"
