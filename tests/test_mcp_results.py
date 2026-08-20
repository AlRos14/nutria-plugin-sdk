from __future__ import annotations

import pytest

from nutria_plugin.mcp_results import (
    MCPResultContractError,
    normalize_mcp_result,
    validate_capability_result,
    validate_declared_outputs,
)


def test_normalizes_fastmcp_json_string_result_envelope() -> None:
    payload = normalize_mcp_result(
        structured_content={
            "result": '{"ok":true,"chats":[{"chat_ref":"chat-1"}]}'
        },
        text_content="ignored",
    )

    assert payload == {"ok": True, "chats": [{"chat_ref": "chat-1"}]}


def test_preserves_provider_owned_result_object() -> None:
    payload = normalize_mcp_result(
        structured_content={"result": {"id": "op-1"}, "status": "complete"}
    )

    assert payload == {"result": {"id": "op-1"}, "status": "complete"}


def test_validates_nested_many_output() -> None:
    validate_declared_outputs(
        {"data": {"items": [{"id": "item-1"}]}},
        [{"result_path": ".data.items", "many": True}],
    )


def test_rejects_missing_declared_output() -> None:
    with pytest.raises(
        MCPResultContractError,
        match=r"declared output path did not materialize: \.chats",
    ):
        validate_declared_outputs(
            {"result": '{"chats":[]}'},
            [{"result_path": ".chats", "many": True}],
        )


def test_rejects_non_list_many_output() -> None:
    with pytest.raises(MCPResultContractError, match="many output is not a list"):
        validate_declared_outputs(
            {"messages": {"id": "message-1"}},
            [{"result_path": ".messages", "many": True}],
        )


def test_validates_capability_against_protocol_values() -> None:
    capability = {
        "produces": [
            {"result_path": ".chats", "resource_type": "whatsapp_chat", "many": True}
        ]
    }

    payload = validate_capability_result(
        capability,
        structured_content={"result": '{"ok":true,"chats":[]}'},
    )

    assert payload == {"ok": True, "chats": []}
