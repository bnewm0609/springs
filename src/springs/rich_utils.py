from typing import Any, Dict, Optional, Sequence, Union

from omegaconf import DictConfig, ListConfig
from rich.console import Console
from rich.table import Column, Table
from rich.traceback import install
from rich.tree import Tree

from .core import traverse
from .utils import SpringsConfig


def add_pretty_traceback():
    # setup nice traceback through rich library
    install(show_locals=SpringsConfig.RICH_LOCALS)


def print_table(
    title: str,
    columns: Sequence[str],
    values: Sequence[Sequence[Any]],
    colors: Optional[Sequence[str]] = None,
):
    colors = list(
        colors or ["magenta", "cyan", "red", "green", "yellow", "blue"]
    )
    if len(columns) > len(colors):
        # repeat colors if we have more columns than colors
        colors = colors * (len(columns) // len(colors) + 1)

    table = Table(
        *(
            Column(column, justify="center", style=color, vertical="middle")
            for column, color in zip(columns, colors)
        ),
        title=f"\n{title}",
        min_width=len(title) + 2,
    )
    for row in values:
        table.add_row(*row)

    Console().print(table)


def print_tree(title: str, config: Union[DictConfig, ListConfig]):
    def get_parent_path(path: str) -> str:
        return path.rsplit(".", 1)[0] if "." in path else ""

    trees: Dict[str, Tree] = {"": (root := Tree(f"[bold]\n{title}[/bold]"))}

    all_nodes = sorted(
        traverse(config, include_nodes=True, include_leaves=False),
        key=lambda spec: spec.path.count("."),
    )
    for spec in all_nodes:
        parent_path = get_parent_path(spec.path)
        tree = trees.get(parent_path, None)
        if spec.key is None or tree is None:
            raise ValueError("Cannot print disjoined tree")

        color = "magenta" if isinstance(spec.value, DictConfig) else "cyan"
        repr_ = spec.key if isinstance(spec.key, str) else f"[{spec.key}]"

        subtree = tree.add(label=f"[bold {color}]{repr_}[/bold {color}]")
        trees[spec.path] = subtree

    for spec in traverse(config, include_nodes=False, include_leaves=True):
        tree = trees.get(get_parent_path(spec.path), None)
        if tree is None:
            raise ValueError("Cannot print disjoined tree")

        tree.add(
            label=(
                f"[bold]{spec.key}[/bold] "
                f"([italic]{spec.type.__name__}[/italic]) "
                f"= {spec.value}"
            )
        )

    Console().print(root)
