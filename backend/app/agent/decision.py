import re
from typing import Any


# ============================================================
# AGENT DECISION / PLANNING LAYER
# ============================================================


def normalize_query(query: str) -> str:
    """
    Normalize a customer query for intentdetection.
    """
    if not query:
        return ""

    text = query.lower().strip()
    text = re.sub(r"\s+", " ", text)

    return text


def extract_order_number(query: str) -> str | None:
    """
    Extract an order number such as ORD1002.
    """
    if not query:
        return None

    match = re.search(
        r"\bORD\d+\b",
        query,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(0).upper()


def extract_product_id(query: str) -> int| None:
    """
    Extract a numeric product ID from queries such as:

    product 5
    product ID 5
    details of product 5
    """
    if not query:
        return None

    match = re.search(
        r"\b(?:product\s*(?:id)?\s*)?(\d+)\b",
        query.lower(),
    )

    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def detect_product_query(query: str) -> str | None:
    """
    Detect common product/category terms.
    """
    text = normalize_query(query)

    product_keywords = [
        "keyboard",
        "keyboards",
        "mouse",
        "mice",
        "laptop",
        "laptops",
        "monitor",
        "monitors",
        "webcam",
        "webcams",
        "headphone",
        "headphones",
        "earphone",
        "earphones",
        "earbuds",
        "speaker",
        "speakers",
        "phone",
        "phones",
        "smartphone",
        "smartphones",
        "tablet",
        "tablets",
        "charger",
        "chargers",
        "cable",
        "cables",
        "adapter",
        "adapters",
        "hub",
        "hubs",
        "usb",
        "usb-c",
        "usb c",
        "type-c",
        "type c",
        "power bank",
        "powerbank",
        "watch",
        "watches",
        "smartwatch",
        "smartwatches",
        "camera",
        "cameras",
        "printer",
        "printers",
        "router",
        "routers",
        "ssd",
        "hard drive",
        "hard drives",
        "storage",
    ]

    for keyword in product_keywords:
        if keyword in text:
            return keyword

    return None


def detect_policy_intent(query: str) -> str | None:
    """
    Detect the main knowledge-base policytopic.
    """
    text = normalize_query(query)
    words = set(text.split())

    if words.intersection(
        {
            "cancel",
            "cancelled",
            "canceled",
            "cancellation",
        }
    ):
        return "cancellation"

    if words.intersection(
        {
            "return",
            "returns",
            "returned",
        }
    ):
        return "return"

    if words.intersection(
        {
            "refund",
            "refunds",
            "refunded",
        }
    ):
        return "refund"

    if words.intersection(
        {
            "warranty",
            "warranties",
        }
    ):
        return "warranty"

    if words.intersection(
        {
            "shipping",
            "delivery",
            "delivered",
            "deliver",
        }
    ):
        return "shipping"

    if words.intersection(
        {
            "damage",
            "damaged",
        }
    ):
        return "damage"

    return None


def detect_order_policy_query(query: str)-> bool:
    """
    Detect queries that require both:
    1. Order information
    2. Knowledge-base/policy information

    Example:
    "Check order ORD1002 and tell me whether I should contact
    support because it is delayed."
    """
    text = normalize_query(query)

    order_number = extract_order_number(query)

    order_reference = (
        order_number is not None
        or "my order" in text
        or "this order" in text
        or "the order" in text
    )

    policy_action_phrases = [
        "should i contact support",
        "should i contact customer support",
        "do i need to contact support",
        "do i need to contact customer support",
        "should i contact you",
        "what should i do",
        "what can i do",
        "do i need help",
        "should i raise a ticket",
        "should i create a ticket",
        "should i open a ticket",
        "is it delayed",
        "is my order delayed",
        "because it is delayed",
        "because it's delayed",
        "because it was delayed",
        "because it has been delayed",
    ]

    asks_policy_action = any(
        phrase in text
        for phrase in policy_action_phrases
    )

    return order_reference and asks_policy_action


def create_plan(
    intent: str,
    *,
    requires_memory: bool = False,
) -> list[str]:
    """
    Create an explicit execution plan forthe selected intent.
    """

    plans = {
        "order_status": [
            "identify order",
            "retrieve order status",
            "generate customer response",
        ],
        "order_policy": [
            "identify order",
            "retrieve order status",
            "retrieve relevant order policy",
            "combine order data with policy",
            "generate customer response",
        ],
        "create_ticket": [
            "identify support issue",
            "create support ticket",
            "generate customer response",
        ],
        "escalation": [
            "identify escalation request",
            "create high-priority support ticket",
            "mark interaction as escalated",
            "generate escalation response",
        ],
        "ticket_status": [
            "identify ticket",
            "retrieve ticket status",
            "generate customer response",
        ],
        "product_details": [
            "identify product",
            "retrieve product details",
            "generate customer response",
        ],
        "product_search": [
            "identify requested product",
            "search product catalog",
            "generate customer response",
        ],
        "rag": [
            "identify knowledge topic",
            "retrieve relevant knowledge",
            "generate customer response",
        ],
    }

    plan = list(
        plans.get(
            intent,
            [
                "analyze customer request",
                "retrieve relevant information",
                "generate customer response",
            ],
        )
    )

    if requires_memory:
        plan.insert(
            0,
            "resolve missing context fromconversation memory",
        )

    return plan


def make_agent_decision(
    query: str,
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Analyze a customer query and produce a structured
    agent decision.

    This layer does not execute tools.

    It only decides:

    - intent
    - confidence
    - entities
    - selected tool
    - memory requirement
    - execution plan
    """

    text = normalize_query(query)
    memory = memory or {}

    order_number = extract_order_number(query)
    product_id = extract_product_id(query)
    product_keyword = detect_product_query(query)
    policy_intent = detect_policy_intent(query)

    # --------------------------------------------------------
    # FOLLOW-UP ORDER REQUEST
    # --------------------------------------------------------

    followup_order_phrases = [
        "when will it arrive",
        "when will my order arrive",
        "when is it arriving",
        "when will this arrive",
        "when should it arrive",
        "what is the delivery date",
        "when is the delivery",
        "when can i expect it",
        "when can i expect my order",
        "when should i receive it",
        "when will i receive it",
        "when will i get it",
    ]

    is_order_followup = any(
        phrase in text
        for phrase in followup_order_phrases
    )

    if is_order_followup and memory.get("last_order_number"):
        remembered_order = memory["last_order_number"]

        return {
            "intent": "order_status",
            "confidence": 0.94,
            "entities": {
                "order_number": remembered_order,
            },
            "tool": "get_order_status",
            "requires_memory": True,
            "plan": create_plan(
                "order_status",
                requires_memory=True,
            ),
        }

    # --------------------------------------------------------
    # MULTI-STEP ORDER + POLICY QUERY
    # --------------------------------------------------------

    if detect_order_policy_query(query):
        remembered_order = (
            order_number
            or memory.get("last_order_number")
        )

        requires_memory = (
            order_number is None
            and memory.get("last_order_number") is not None
        )

        return {
            "intent": "order_policy",
            "confidence": 0.97,
            "entities": {
                "order_number": remembered_order,
                "policy_topic": "shipping",
            },
            "tool": "get_order_status",
            "requires_memory": requires_memory,
            "plan": create_plan(
                "order_policy",
                requires_memory=requires_memory,
            ),
        }

    # --------------------------------------------------------
    # HUMAN ESCALATION
    # --------------------------------------------------------

    escalation_phrases = [
        "i want to speak to a human",
        "i want to talk to a human",
        "speak to a human",
        "talk to a human",
        "connect me to a human",
        "connect me with a human",
        "i need a human agent",
        "i need a human",
        "speak to a human agent",
        "talk to a human agent",
        "connect me to an agent",
        "connect me with an agent",
        "i need an agent",
        "i need a representative",
        "connect me to a representative",
        "connect me with a representative",
        "speak to a representative",
        "talk to a representative",
        "please escalate this",
        "escalate this",
        "i want human support",
        "i need human support",
    ]

    if any(
        phrase in text
        for phrase in escalation_phrases
    ):
        return {
            "intent": "escalation",
            "confidence": 0.98,
            "entities": {},
            "tool": "create_support_ticket",
            "requires_memory": False,
            "plan": create_plan("escalation"),
        }

    # --------------------------------------------------------
    # CREATE SUPPORT TICKET
    # --------------------------------------------------------

    ticket_phrases = [
        "create ticket",
        "create a ticket",
        "support ticket",
        "raise a ticket",
        "raise ticket",
        "open a ticket",
        "open ticket",
    ]

    if any(
        phrase in text
        for phrase in ticket_phrases
    ):
        return {
            "intent": "create_ticket",
            "confidence": 0.97,
            "entities": {},
            "tool": "create_support_ticket",
            "requires_memory": False,
            "plan": create_plan("create_ticket"),
        }

    # --------------------------------------------------------
    # TICKET STATUS
    # --------------------------------------------------------

    if (
        "ticket" in text
        and (
            "status" in text
            or "check" in text
            or "track" in text
        )
    ):
        ticket_id_match = re.search(
            r"\bticket\s*#?\s*(\d+)\b",
            text,
        )

        ticket_id = (
            int(ticket_id_match.group(1))
            if ticket_id_match
            else memory.get("last_ticket_id")
        )

        requires_memory = (
            ticket_id_match is None
            and ticket_id is not None
        )

        return {
            "intent": "ticket_status",
            "confidence": 0.95,
            "entities": {
                "ticket_id": ticket_id,
            },
            "tool": "get_ticket_status",
            "requires_memory": requires_memory,
            "plan": create_plan(
                "ticket_status",
                requires_memory=requires_memory,
            ),
        }

    # --------------------------------------------------------
    # ORDER STATUS
    # --------------------------------------------------------

    if (
        "order" in text
        and (
            "status" in text
            or "where" in text
            or "track" in text
            or "delivery" in text
        )
    ):
        requires_memory = (
            order_number is None
            and memory.get("last_order_number") is not None
        )

        return {
            "intent": "order_status",
            "confidence": 0.96,
            "entities": {
                "order_number": (
                    order_number
                    or memory.get("last_order_number")
                ),
            },
            "tool": "get_order_status",
            "requires_memory": requires_memory,
            "plan": create_plan(
                "order_status",
                requires_memory=requires_memory,
            ),
        }

    # --------------------------------------------------------
    # PRODUCT DETAILS
    # --------------------------------------------------------

    if (
        "product details" in text
        or "details of product" in text
        or "product information" in text
    ):
        requires_memory = (
            product_id is None
            and memory.get("last_product_id") is not None
        )

        return {
            "intent": "product_details",
            "confidence": 0.95,
            "entities": {
                "product_id": (
                    product_id
                    or memory.get("last_product_id")
                ),
            },
            "tool": "get_product_details",
            "requires_memory": requires_memory,
            "plan": create_plan(
                "product_details",
                requires_memory=requires_memory,
            ),
        }

    # --------------------------------------------------------
    # PRODUCT SEARCH
    # --------------------------------------------------------

    product_intent_phrases = [
        "do you have",
        "do you sell",
        "is there",
        "is there any",
        "are there",
        "can i buy",
        "i want",
        "i need",
        "looking for",
        "looking to buy",
        "find me",
        "show me",
        "available",
        "availability",
        "in stock",
        "stock available",
        "what products",
        "which products",
        "what devices",
        "how much is",
        "how much does",
        "what is the price",
        "price of",
        "cost of",
    ]

    matched_product_intent = any(
        phrase in text
        for phrase in product_intent_phrases
    )

    if product_keyword or matched_product_intent:
        search_query = (
            product_keyword
            or query.strip()
        )

        normalized_search_query = (
            search_query
            .lower()
            .replace("usb c", "usb-c")
            .replace("type c", "type-c")
        )

        if (
            "usb-c" in normalized_search_query
            and "hub" in normalized_search_query
        ):
            search_query = "USB-C hub"

        elif (
            "usb" in normalized_search_query
            and "hub" in normalized_search_query
        ):
            search_query = "USB-C hub"

        elif (
            "type-c" in normalized_search_query
            and "hub" in normalized_search_query
        ):
            search_query = "USB-C hub"

        return {
            "intent": "product_search",
            "confidence": 0.96,
            "entities": {
                "product_query": search_query,
            },
            "tool": "search_products",
            "requires_memory": False,
            "plan": create_plan("product_search"),
        }

    # --------------------------------------------------------
    # KNOWLEDGE BASE / RAG
    # --------------------------------------------------------

    if policy_intent:
        return {
            "intent": "rag",
            "confidence": 0.93,
            "entities": {
                "policy_topic": policy_intent,
            },
            "tool": "search_knowledge_base",
            "requires_memory": False,
            "plan": create_plan("rag"),
        }

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    return {
        "intent": "rag",
        "confidence": 0.55,
        "entities": {},
        "tool": "search_knowledge_base",
        "requires_memory": False,
        "plan": create_plan("rag"),
    }
