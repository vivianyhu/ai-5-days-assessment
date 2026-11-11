# tests/test_agent.py
"""Automated regression testing suite checking schema validation and tool output."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import fetch_industry_trends_by_category, TrendAnalysisInput

def test_fetch_trends_success():
    """Verify tool success outcome on correct indexed parameters."""
    output = fetch_industry_trends_by_category(category="technology", max_results=1)
    assert output["status"] == "success"
    assert len(output["data"]) == 1
    assert "Agentic AI" in output["data"][0]["title"]

def test_fetch_trends_guided_error():
    """Verify tool returns a descriptive recovery instruction for incorrect categories."""
    output = fetch_industry_trends_by_category(category="gardening", max_results=1)
    assert output["status"] == "error"
    assert "recovery_suggestion" in output
    assert "Available categories are" in output["recovery_suggestion"]

def test_schema_constraints():
    """Verify Pydantic strict schemas block invalid inputs."""
    with pytest.raises(Exception):
        # max_results constraints: upper limit is 5
        TrendAnalysisInput(category="technology", max_results=99)
