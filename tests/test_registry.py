"""
Tests for the connector registry: listing, sync-all behavior, and
credential state reporting.
"""
import pytest

from agent.connectors import list_connectors, get_connector, sync_all
from agent.connectors.local import LocalFileConnector


class TestRegistry:
    def test_lists_connectors(self):
        connectors = list_connectors()
        ids = {c["id"] for c in connectors}
        assert "local" in ids
        assert "google" in ids
        # every connector reports credential state
        for c in connectors:
            assert "configured" in c
            assert "has_credentials" in c

    def test_get_connector(self):
        assert isinstance(get_connector("local"), LocalFileConnector)
        with pytest.raises(KeyError):
            get_connector("nope")

    @pytest.mark.asyncio
    async def test_sync_all_handles_sync_connectors(self):
        """sync_all must not crash on the always-configured local connector
        (regression: sync() was sync while sync_all awaited it)."""
        results = await sync_all()
        assert "local" in results
        assert results["local"].errors == []
