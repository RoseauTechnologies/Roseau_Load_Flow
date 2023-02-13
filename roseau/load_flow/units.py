"""
Units registry used by Roseau Load Flow using the `pint`_ package.

.. _pint: https://pint.readthedocs.io/en/stable/getting/overview.html
"""
from pint import UnitRegistry

ureg = UnitRegistry()
"""The :class:`~pint.UnitRegistry` to use in this project"""

Q_ = ureg.Quantity
"""The :class:`~pint.Quantity` class to use in this project"""
