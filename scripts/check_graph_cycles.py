#!/usr/bin/env python3
"""Utility to detect cycles and unreachable nodes in a compiled LangGraph.

This is a development helper — not part of the main library. Run it against
an exported graph definition to catch structural issues before deploying.

Usage::

    python scripts/check_graph_cycles.py --module my_agent.graph --attr graph
"""

from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any


def get_graph_edges(graph: Any) -> list[tuple[str, str]]:
    """Extract edges from a compiled LangGraph graph object.

    Args:
        graph: A compiled ``StateGraph`` or ``CompiledGraph`` instance.

    Returns:
        List of ``(source, target)`` edge tuples.
    """
    edges: list[tuple[str, str]] = []
    # Compiled graphs expose edges via the internal _graph attribute.
    internal = getattr(graph, "_graph", None) or getattr(graph, "graph", None)
    if internal is None:
        raise ValueError(
            "Cannot inspect graph edges: no _graph or graph attribute found."
        )
    for source, target_map in internal._edges.items():
        if isinstance(target_map, dict):
            for target in target_map.values():
                edges.append((source, target))
        else:
            edges.append((source, target_map))
    return edges


def find_cycles(edges: list[tuple[str, str]]) -> list[list[str]]:
    """Find all simple cycles in a directed graph represented as an edge list.

    Uses depth-first search with a recursion stack.

    Args:
        edges: List of ``(source, target)`` pairs.

    Returns:
        List of cycles, where each cycle is a list of node names.
    """
    adjacency: dict[str, list[str]] = {}
    for src, tgt in edges:
        adjacency.setdefault(src, []).append(tgt)

    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.append(node)
        for neighbour in adjacency.get(node, []):
            if neighbour not in visited:
                dfs(neighbour)
            elif neighbour in rec_stack:
                cycle_start = rec_stack.index(neighbour)
                cycles.append(list(rec_stack[cycle_start:]))
        rec_stack.pop()

    for node in list(adjacency):
        if node not in visited:
            dfs(node)

    return cycles


def main() -> None:
    """Entry point for the cycle-detection script."""
    parser = argparse.ArgumentParser(
        description="Detect cycles in a LangGraph graph definition."
    )
    parser.add_argument(
        "--module",
        required=True,
        help="Dotted module path containing the compiled graph (e.g. my_agent.graph).",
    )
    parser.add_argument(
        "--attr",
        default="graph",
        help="Attribute name of the compiled graph inside the module.",
    )
    args = parser.parse_args()

    try:
        mod = importlib.import_module(args.module)
    except ImportError as exc:
        print(f"ERROR: Could not import module '{args.module}': {exc}", file=sys.stderr)
        sys.exit(1)

    graph = getattr(mod, args.attr, None)
    if graph is None:
        print(
            f"ERROR: Attribute '{args.attr}' not found in '{args.module}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        edges = get_graph_edges(graph)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    cycles = find_cycles(edges)
    if cycles:
        print(f"Found {len(cycles)} cycle(s):")
        for i, cycle in enumerate(cycles, 1):
            print(f"  {i}. {' -> '.join(cycle)} -> {cycle[0]}")
        sys.exit(1)
    else:
        print("No cycles detected. Graph structure looks clean.")
        sys.exit(0)


if __name__ == "__main__":
    main()
