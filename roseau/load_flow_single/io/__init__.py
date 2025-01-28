"""
This module provides functions to read and write networks from and to different formats.

You do not need to use this module directly, you can read and write networks using the
corresponding methods of the :class:`~roseau.load_flow_single.ElectricalNetwork` object.
"""

from roseau.load_flow_single.io.dict import network_from_dict, network_to_dict

__all__ = ["network_to_dict", "network_from_dict"]
