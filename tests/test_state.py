from operator import add

from src.state import Finding, ResearchState


def test_finding_shape():
    finding: Finding = {
        "source": "https://example.com",
        "claim": "Ollama serves models locally.",
        "confidence": 0.9,
    }
    assert finding["confidence"] == 0.9


def test_research_state_shape():
    state: ResearchState = {
        "question": "What is LangGraph?",
        "findings": [],
        "report": "",
        "next_agent": "researcher",
        "iterations": 0,
    }
    assert state["iterations"] == 0
    assert state["findings"] == []


def test_findings_reducer_appends_rather_than_overwrites():
    """This is the exact reducer LangGraph uses to merge the Researcher's
    writes across multiple turns (learning guide §2.3) — a second turn's
    findings must be appended, not replace the first turn's."""
    turn_one: list[Finding] = [
        {"source": "a", "claim": "x", "confidence": 0.5},
    ]
    turn_two: list[Finding] = [
        {"source": "b", "claim": "y", "confidence": 0.8},
    ]

    merged = add(turn_one, turn_two)

    assert merged == turn_one + turn_two
    assert len(merged) == 2
