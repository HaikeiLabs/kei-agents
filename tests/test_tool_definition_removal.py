"""The agent package must not own a second tool-definition catalog."""

from importlib.util import find_spec
from pathlib import Path


def test_agents_does_not_ship_a_tool_definition_catalog():
    assert find_spec("agents.tool_definitions") is None
    connectors = Path(__file__).parents[1] / "src" / "agents" / "connectors"
    assert not list(connectors.glob("*.py"))

