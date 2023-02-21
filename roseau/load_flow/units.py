"""
Units registry used by Roseau Load Flow using the `pint`_ package.

.. class:: ureg

    The :class:`~pint.UnitRegistry` object to use in this project.

.. class:: Q_

    The :class:`~pint.Quantity` class to use in this project.

.. _pint: https://pint.readthedocs.io/en/stable/getting/overview.html
"""
from pint import UnitRegistry

ureg = UnitRegistry(
    preprocessors=[
        lambda s: s.replace("%", " percent "),
    ]
)

Q_ = ureg.Quantity

# Define the percent unit
ureg.define("percent = 0.01 = %")
