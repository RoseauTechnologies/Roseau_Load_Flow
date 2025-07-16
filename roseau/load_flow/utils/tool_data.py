import json
from collections.abc import Iterator

from roseau.load_flow.typing import JsonDict


class ToolData:
    def __init__(self) -> None:
        self._storage: dict[str, JsonDict] = {}

    def __repr__(self) -> str:
        return f"ToolData({self._storage!r})"

    @staticmethod
    def _check_tool(tool: str, /) -> None:
        """Check if the tool name is a valid."""
        if not isinstance(tool, str):
            raise TypeError(f"Tool name must be a string, got {type(tool).__name__}.")

    @staticmethod
    def _check_metadata(data: JsonDict, /) -> None:
        """Check if the data is a valid dictionary and can be serialized to JSON."""
        if not isinstance(data, dict):
            raise TypeError(f"ToolData must be a dictionary, got {type(data).__name__}.")
        try:
            json.dumps(data, ensure_ascii=False)  # Check if it can be serialized to JSON
        except (TypeError, ValueError) as e:
            raise ValueError(f"ToolData is not serializable to JSON: {e}") from e

    def __getitem__(self, tool: str, /) -> JsonDict:
        """Get the data of a tool."""
        self._check_tool(tool)
        if tool not in self._storage:
            raise KeyError(f"No data found for tool {tool!r}.")
        return self._storage[tool]

    def __contains__(self, tool: str, /) -> bool:
        try:
            self[tool]
        except KeyError:
            return False
        return True

    def __len__(self) -> int:
        """Return the number of tools with data."""
        return len(self._storage)

    def __iter__(self) -> Iterator[str]:
        """Return an iterator over the tool names."""
        return iter(self._storage)

    def _ipython_key_completions_(self) -> list[str]:
        """Return a list of tool names for IPython tab completion."""
        return list(self._storage)

    def add(self, tool: str, data: JsonDict, *, overwrite: bool = False) -> None:
        """Add data for a new tool."""
        self._check_tool(tool)
        self._check_metadata(data)
        if tool in self._storage and not overwrite:
            raise KeyError(f"ToolData for {tool!r} already exists. Use `update` or set `overwrite=True` to replace it.")
        self._storage[tool] = data

    def update(self, tool: str, data: JsonDict) -> None:
        """Update the data of an existing tool."""
        self._check_tool(tool)
        self._check_metadata(data)
        if tool not in self._storage:
            raise KeyError(f"ToolData for {tool!r} does not exist. Use `add` to create it.")
        self._storage[tool].update(data)

    def remove(self, tool: str, missing_ok: bool = False) -> None:
        """Remove the data of a tool."""
        self._check_tool(tool)
        if tool in self._storage:
            del self._storage[tool]
        elif not missing_ok:
            raise KeyError(f"ToolData for {tool!r} does not exist.")

    def clear(self) -> None:
        """Clear all tool data."""
        self._storage.clear()

    def to_dict(self) -> JsonDict:
        """Convert the tool data to a dictionary."""
        return self._storage.copy()
