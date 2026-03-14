from __future__ import annotations

from cashclaw_adapter.config import Settings


def test_memgraph_url_uses_plain_bolt_by_default() -> None:
    settings = Settings(memgraph_host="odin", memgraph_port=7687, memgraph_encrypted=False)
    assert settings.memgraph_url == "bolt://odin:7687"


def test_memgraph_url_uses_secure_bolt_when_encrypted() -> None:
    settings = Settings(memgraph_host="odin", memgraph_port=7687, memgraph_encrypted=True)
    assert settings.memgraph_url == "bolt+s://odin:7687"
