from typing import Dict, List, Any


# ============================================================
# SIMPLE IN-MEMORY CONVERSATION STORE
# ============================================================

conversation_store: Dict[str, List[Dict[str, Any]]] = {}


def get_session_key(
    customer_id: int | None = None,
    session_id: str | None = None,
) -> str:
    """
    Create a unique key for the conversation.

    Priority:
    1. session_id
    2. customer_id
    3. anonymous session
    """

    if session_id:
        return f"session:{session_id}"

    if customer_id is not None:
        return f"customer:{customer_id}"

    return "anonymous"


def get_conversation(
    customer_id: int | None = None,
    session_id: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Return the conversation history for a session.
    """

    key = get_session_key(
        customer_id=customer_id,
        session_id=session_id,
    )

    return conversation_store.get(key, [])


def add_message(
    role: str,
    content: str,
    customer_id: int | None = None,
    session_id: str | None = None,
    metadata: Dict[str, Any] | None = None,
):
    """
    Add a message to the conversation history.
    """

    key = get_session_key(
        customer_id=customer_id,
        session_id=session_id,
    )

    if key not in conversation_store:
        conversation_store[key] = []

    message = {
        "role": role,
        "content": content,
    }

    if metadata:
        message["metadata"] = metadata

    conversation_store[key].append(message)


def get_last_message(
    customer_id: int | None = None,
    session_id: str | None = None,
):
    """
    Return the most recent message.
    """

    history = get_conversation(
        customer_id=customer_id,
        session_id=session_id,
    )

    if not history:
        return None

    return history[-1]


def get_last_agent_result(
    customer_id: int | None = None,
    session_id: str | None = None,
):
    """
    Return metadata from the most recent agent response.
    """

    history = get_conversation(
        customer_id=customer_id,
        session_id=session_id,
    )

    for message in reversed(history):

        if (
            message.get("role") == "assistant"
            and message.get("metadata")
        ):
            return message["metadata"]

    return None


def clear_conversation(
    customer_id: int | None = None,
    session_id: str | None = None,
):
    """
    Clear conversation history for a session.
    """

    key = get_session_key(
        customer_id=customer_id,
        session_id=session_id,
    )

    conversation_store.pop(key, None)