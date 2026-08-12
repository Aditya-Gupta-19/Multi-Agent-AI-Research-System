"""Shared state schema for the research graph.

Every node (Supervisor, Researcher, Analyst, Writer) reads from and writes
back into one ResearchState. See the learning guide, Module 2 §2.3, for the
full design rationale — this file is the literal implementation of it.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict


class Finding(TypedDict):
    """One piece of evidence the Researcher agent collected."""

    source: str
    claim: str
    confidence: float


class ResearchState(TypedDict):
    """Shared state passed between every node in the graph."""

    question: str

    # `add` is the reducer: LangGraph appends a node's returned findings to
    # this list instead of overwriting it, since the Researcher writes here
    # more than once per run (§2.3).
    findings: Annotated[list[Finding], add]

    report: str
    next_agent: str
    iterations: int
