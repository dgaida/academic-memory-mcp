"""Tests for the Agent class."""
import pytest
from mcp_university.agent.engine import Agent

def test_agent_initialization():
    """Tests the initialization of the Agent class."""
    agent = Agent()
    assert agent is not None
