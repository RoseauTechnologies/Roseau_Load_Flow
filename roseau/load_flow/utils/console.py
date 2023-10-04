from rich.console import Console

console = Console()

palette = [
    "#4c72b0",
    "#dd8452",
    "#55a868",
    "#c44e52",
    "#8172b3",
    "#937860",
    "#da8bc3",
    "#8c8c8c",
    "#ccb974",
    "#64b5cd",
]
"""Color palette for the catalogue tables.

This is seaborn's default color palette. Generated with:
```python
import seaborn as sns
sns.set_theme()
list(sns.color_palette().as_hex())
```
"""
