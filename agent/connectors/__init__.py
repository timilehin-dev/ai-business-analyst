"""
Connector Registry.

Central access point for all data connectors. The API and the background
sync task use this to enumerate and run connectors.
"""
from typing import Dict, List

from agent.connectors.base import BaseConnector, ConnectorResult
from agent.connectors.local import LocalFileConnector
from agent.connectors.google import GoogleConnector

# Order matters for the UI: local first, then Google.
_CONNECTORS: List[BaseConnector] = [
    LocalFileConnector(),
    GoogleConnector(),
]


def get_connector(connector_id: str) -> BaseConnector:
    for c in _CONNECTORS:
        if c.id == connector_id:
            return c
    raise KeyError(f"Unknown connector: {connector_id}")


def list_connectors() -> List[dict]:
    return [c.describe() for c in _CONNECTORS]


def configured_connectors() -> List[BaseConnector]:
    return [c for c in _CONNECTORS if c.is_configured()]


async def sync_all() -> Dict[str, ConnectorResult]:
    """Run every configured connector. Used by the continuous sync task."""
    results: Dict[str, ConnectorResult] = {}
    for c in configured_connectors():
        try:
            results[c.id] = await c.sync()
        except Exception as e:  # one connector failing must not stop the rest
            results[c.id] = ConnectorResult(connector_id=c.id, errors=[str(e)], message=str(e))
    return results