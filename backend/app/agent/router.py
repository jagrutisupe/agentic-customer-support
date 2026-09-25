import json
import re
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.decision import make_agent_decision
from app.database.models import Conversation, Message, AgentLog, SupportTicket

from app.tools.order_tools import get_order_status
from app.tools.product_tools import (
    search_products,
    get_product_details,
)
from app.tools.ticket_tools import (
    create_support_ticket,
    get_ticket_status,
)
from app.rag.rag_tools import search_knowledge_base

# ============================================================
# INPUT SCOPE GUARDRAIL
# ============================================================

def is_customer_support_query(query: str) -> bool:
    """
    Determine whether a query is related to the customer-support
    capabilities of this application.

    This is intentionally rule-based so that unsupported requests
    are rejected before any database or RAG tool is executed.
    """

    text = query.lower().strip()

    if not text:
        return False

    support_keywords = [
        # Orders
        "order",
        "orders",
        "ord",
        "delivery",
        "delivered",
        "shipping",
        "shipment",
        "track",
        "tracking",

        # Products
        "product",
        "products",
        "price",
        "cost",
        "stock",
        "available",
        "availability",
        "buy",
        "purchase",

        # Returns / refunds
        "return",
        "returns",
        "refund",
        "refunded",
        "exchange",

        # Warranty / damage
        "warranty",
        "damaged",
        "damage",
        "broken",
        "defective",

        # Cancellation
        "cancel",
        "cancelled",
        "canceled",
        "cancellation",

        # Support
        "support",
        "help",
        "issue",
        "problem",
        "complaint",
        "ticket",
        "customer service",

        # Human escalation
"escalate",
"escalation",
"human agent",
"human support",
"human representative",
"representative",
"speak to a human",
"speak to human",
"talk to a human",
"talk to human",
"connect me to a human",
"connect me to an agent",
"need a human agent",
"need a human",
"want to speak to a human",
"want human support",
    ]

    return any(
        keyword in text
        for keyword in support_keywords
    )

# ============================================================
# CONVERSATION MEMORY
# ============================================================

conversation_memory = {}


def get_or_create_conversation(
    db: Session,
    customer_id: int | None,
    session_id: str | None,
):
    """
    Get the persistent Conversation record for a session,
    or create it when it does not exist.
    """

    if not customer_id or not session_id:
        return None

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.session_id == session_id,
        )
        .first()
    )

    if conversation:
        return conversation

    conversation = Conversation(
        customer_id=customer_id,
        session_id=session_id,
        status="active",
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_memory(session_id: str | None):
    """
    Retrieve conversation memory for a session.
    """

    if not session_id:
        return {}

    return conversation_memory.get(
        session_id,
        {},
    )

def save_conversation_messages(
    db: Session,
    conversation,
    query: str,
    response: str,
):
    """Persist the customer query and agent response for a conversation."""

    if conversation is None:
        return

    db.add(
        Message(
            conversation_id=conversation.id,
            sender="customer",
            message=query,
        )
    )

    if response:
        db.add(
            Message(
                conversation_id=conversation.id,
                sender="agent",
                message=response,
            )
        )

    conversation.updated_at = datetime.utcnow()
    db.commit()



def save_agent_log(
    db: Session,
    conversation,
    query: str,
    decision: dict | None,
    agent: str,
    tool: str | None,
    result: dict,
    trace: list[str],
    response: str,
    latency_ms: float,
):
    """Persist one complete agent execution to PostgreSQL."""

    if conversation is None:
        return

    last_log = (
        db.query(AgentLog)
        .filter(AgentLog.conversation_id == conversation.id)
        .order_by(AgentLog.iteration.desc())
        .first()
    )
    iteration = (last_log.iteration + 1) if last_log else 1

    success = result.get("success", True)

    log = AgentLog(
        conversation_id=conversation.id,
        iteration=iteration,
        intent=(
            decision.get("intent")
            if decision
            else agent
        ),
        action=agent,
        tool_name=tool,
        tool_input={
            "query": query,
        },
        tool_output={
    "result": json.loads(json.dumps(result, default=str)),
    "response": response,
    "trace": trace,
},
        latency_ms=round(latency_ms, 2),
        status="success" if success else "failed",
        escalated=(
            agent in {
                "guardrail",
                "escalation",
            }
            or result.get("escalated", False)
        ),
    )

    db.add(log)
    db.commit()


def update_memory(
    session_id: str | None,
    data: dict,
):
    """
    Update conversation memory for a session.
    """

    if not session_id:
        return

    if session_id not in conversation_memory:
        conversation_memory[session_id] = {}

    conversation_memory[session_id].update(data)


# ============================================================
# RESPONSE HELPERS
# ============================================================

def build_response(
    *,
    query: str,
    agent: str,
    tool: str | None,
    result: dict,
    db: Session,
    conversation=None,
    response: str,
    memory_enabled: bool,
    session_id: str | None,
    customer_id: int | None,
    context_used: bool,
    trace: list[str],
    decision: dict | None = None,
    latency_ms: float = 0.0,
):
    """
    Standard response structure returned by the agent.
    """

    if conversation is not None:
        save_conversation_messages(
            db=db,
            conversation=conversation,
            query=query,
            response=response,
        )

        save_agent_log(
            db=db,
            conversation=conversation,
            query=query,
            decision=decision,
            agent=agent,
            tool=tool,
            result=result,
            trace=trace,
            response=response,
            latency_ms=latency_ms,
        )

    return {
        "success": result.get("success", True),
        "query": query,
        "agent": agent,
        "tool": tool,
        "response": response,
        "decision": decision,

        "memory": {
            "enabled": memory_enabled,
            "session_id": session_id,
            "customer_id": customer_id,
            "context_used": context_used,
        },

        "trace": {
            f"step_{index + 1}": step
            for index, step in enumerate(trace)
        },

        "result": result,
    }


def order_response(result: dict) -> str:
    """
    Convert order tool result into a user-friendly response.
    """

    if not result.get("success"):
        return result.get(
            "message",
            result.get(
                "error",
                "I could not retrieve the order information.",
            ),
        )

    order = result.get("order")

    if not order:
        return result.get(
            "message",
            "I could not retrieve the order information.",
        )

    order_number = order.get(
        "order_number",
        "your order",
    )

    status = order.get(
        "status",
        "unknown",
    )

    expected_delivery = order.get(
        "expected_delivery",
    )

    total_amount = order.get(
        "total_amount",
    )

    response = (
        f"Order {order_number} is currently "
        f"{status}."
    )

    if expected_delivery:
        response += (
            f" Expected delivery: "
            f"{expected_delivery}."
        )

    if total_amount is not None:
        response += (
            f" Total amount: ₹{total_amount}."
        )

    return response


def product_response(result: dict) -> str:
    """
    Convert product detail result into a user-friendly response.
    """

    if not result.get("success"):
        return result.get(
            "message",
            "I could not retrieve the product information.",
        )

    product = result.get("product")

    if not product:
        return result.get(
            "message",
            "I could not retrieve the product information.",
        )

    name = product.get(
        "name",
        "Product",
    )

    price = product.get(
        "price",
        "N/A",
    )

    category = product.get(
        "category",
        "N/A",
    )

    stock = product.get(
        "stock",
        "N/A",
    )

    warranty = product.get(
        "warranty_months",
        "N/A",
    )

    return (
        f"{name} costs ₹{price}. "
        f"Category: {category}. "
        f"Stock available: {stock}. "
        f"Warranty: {warranty} months."
    )


# ============================================================
# RAG RESPONSE HELPERS
# ============================================================

def normalize_text(value: str) -> str:
    """Normalize text for matching and comparison."""
    if not value:
        return ""

    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def clean_markdown(text: str) -> str:
    """Convert raw Markdown into clean customer-facing text."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n")

    text = re.sub(
        r"^\s*#{1,6}\s*",
        "",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"^\s*[-*]\s+",
        "• ",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            lines.append(line)

    return "\n".join(lines).strip()


def extract_policy_sections(content: str) -> list[dict]:
    """Split retrieved Markdown into logical policy sections."""
    if not content:
        return []

    content = content.replace("\r\n", "\n")

    parts = re.split(
        r"(?=^\s*#{1,6}\s+.+$)",
        content,
        flags=re.MULTILINE,
    )

    sections = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        heading_match = re.match(
            r"^\s*#{1,6}\s+(.+?)\s*$",
            part,
        )

        if heading_match:
            heading = heading_match.group(1).strip()
            body = part[heading_match.end():].strip()
        else:
            heading = ""
            body = part

        body = clean_markdown(body)
        heading = clean_markdown(heading)

        if body:
            sections.append(
                {
                    "heading": heading,
                    "content": body,
                }
            )

    return sections


def detect_policy_intent(query: str) -> str | None:
    """Detect the primary policy topic requested by the customer."""
    text = normalize_text(query)

    # Check cancellation before generic order/delivery concepts.
    if any(word in text.split() for word in [
        "cancel", "cancelled", "canceled", "cancellation"
    ]):
        return "cancellation"

    if any(word in text.split() for word in [
        "return", "returns", "returned"
    ]) or "non returnable" in text or "nonreturnable" in text:
        return "return"

    if any(word in text.split() for word in [
        "refund", "refunds", "refunded"
    ]):
        return "refund"

    if any(word in text.split() for word in [
        "warranty", "warranties"
    ]):
        return "warranty"

    if any(word in text.split() for word in [
        "shipping", "delivery", "delivered", "deliver"
    ]):
        return "shipping"

    if any(word in text.split() for word in [
        "damage", "damaged"
    ]):
        return "damage"

    return None


POLICY_SECTION_KEYWORDS = {
    "cancellation": {
        "cancelled orders",
        "canceled orders",
        "cancellation",
    },
    "return": {
        "return window",
        "eligibility",
        "non-returnable items",
        "non returnable items",
        "return policy",
    },
    "refund": {
        "refunds",
        "refund",
    },
    "warranty": {
        "product warranty",
        "warranty period",
        "warranty claims",
        "warranty exclusions",
    },
    "shipping": {
        "standard delivery",
        "order tracking",
        "expected delivery",
        "delayed orders",
        "delivery problems",
        "shipping and delivery policy",
    },
    "damage": {
        "damaged products",
        "warranty exclusions",
    },
}


def section_matches_intent(
    heading: str,
    content: str,
    intent: str | None,
) -> bool:
    """Return True when a policy section belongs to the requested intent."""
    if not intent:
        return True

    normalized_heading = normalize_text(heading)
    allowed = POLICY_SECTION_KEYWORDS.get(intent, set())

    if any(
        normalized_heading == normalize_text(keyword)
        for keyword in allowed
    ):
        return True

    # Handle small heading variations.
    if intent == "cancellation":
        return "cancel" in normalized_heading or "cancellation" in normalized_heading

    if intent == "return":
        return "return" in normalized_heading or "eligib" in normalized_heading

    if intent == "refund":
        return "refund" in normalized_heading

    if intent == "warranty":
        return "warranty" in normalized_heading

    if intent == "shipping":
        return (
            "delivery" in normalized_heading
            or "shipping" in normalized_heading
            or "tracking" in normalized_heading
        )

    if intent == "damage":
        return "damage" in normalized_heading or "warranty" in normalized_heading

    return False


def content_matches_intent(
    content: str,
    intent: str | None,
) -> bool:
    """Fallback matching for chunks whose heading was split away."""
    text = normalize_text(content)

    if intent == "cancellation":
        return any(phrase in text for phrase in [
            "order is cancelled",
            "order is canceled",
            "reason for cancellation",
            "order has been cancelled",
            "order has been canceled",
        ])

    if intent == "return":
        return any(phrase in text for phrase in [
            "return within 7 days",
            "eligible for return",
            "non returnable",
        ])

    if intent == "refund":
        return any(phrase in text for phrase in [
            "refund will be initiated",
            "refund processing",
            "returned product is inspected",
        ])

    if intent == "warranty":
        return any(phrase in text for phrase in [
            "warranty period",
            "under warranty",
            "warranty claims",
            "warranty exclusions",
        ])

    if intent == "shipping":
        return any(phrase in text for phrase in [
            "standard orders",
            "business days",
            "expected delivery",
            "delayed orders",
            "delivery problems",
        ])

    if intent == "damage":
        return any(phrase in text for phrase in [
            "damaged products",
            "damaged by",
            "accidental damage",
        ])

    return False


def format_rag_response(
    query: str,
    rag_result: dict,
) -> str:
    """
    Convert RAG results into a focused customer-facing answer.

    The retriever may return semantically related chunks. This formatter
    prevents unrelated policy sections from leaking into the final answer.
    """
    if not rag_result.get("success"):
        return rag_result.get(
            "message",
            "I couldn't search the knowledge base.",
        )

    results = rag_result.get("results", [])

    if not results:
        return "I couldn't find a relevant policy in the knowledge base."

    intent = detect_policy_intent(query)
    candidate_sections = []

    for result in results:
        content = result.get("content", "")
        if not content:
            continue

        sections = extract_policy_sections(content)

        if not sections:
            cleaned = clean_markdown(content)
            if cleaned:
                sections = [{
                    "heading": "",
                    "content": cleaned,
                }]

        for section in sections:
            heading = section.get("heading", "")
            section_content = section.get("content", "")

            if not section_content:
                continue

            candidate_sections.append({
                "heading": heading,
                "content": section_content,
                "filename": result.get("filename", ""),
                "distance": result.get("distance"),
            })

    if not candidate_sections:
        return "I couldn't find a relevant answer in the knowledge base."

    # Strict intent filtering. If the query clearly asks about one policy,
    # do not mix in merely related sections from another policy.
    if intent:
        heading_matches = [
            section
            for section in candidate_sections
            if section_matches_intent(
                section["heading"],
                section["content"],
                intent,
            )
        ]

        content_matches = [
            section
            for section in candidate_sections
            if not section_matches_intent(
                section["heading"],
                section["content"],
                intent,
            )
            and content_matches_intent(
                section["content"],
                intent,
            )
        ]

        filtered = heading_matches + content_matches

        if filtered:
            candidate_sections = filtered

    # Remove exact duplicate sections.
    unique_sections = {}

    for section in candidate_sections:
        key = (
            normalize_text(section["heading"]),
            normalize_text(section["content"]),
        )

        if key not in unique_sections:
            unique_sections[key] = section

    candidate_sections = list(unique_sections.values())

    # Prefer sections returned with better vector similarity when available.
    candidate_sections.sort(
        key=lambda item: (
            item.get("distance") is None,
            item.get("distance") if item.get("distance") is not None else float("inf"),
        )
    )

    # Keep the answer focused.
    max_sections = {
        "cancellation": 1,
        "refund": 1,
        "return": 3,
        "warranty": 3,
        "shipping": 3,
        "damage": 2,
    }.get(intent, 2)

    candidate_sections = candidate_sections[:max_sections]

    response_parts = []

    for section in candidate_sections:
        heading = section.get("heading", "")
        content = section.get("content", "").strip()

        if not content:
            continue

        # Keep responses concise without cutting useful policy sentences.
        sentences = re.split(
            r"(?<=[.!?])\s+",
            content,
        )
        sentences = [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]
        content = " ".join(sentences[:5])

        if heading:
            response_parts.append(
                f"**{heading}**\n\n{content}"
            )
        else:
            response_parts.append(content)

    if not response_parts:
        return "I couldn't find a relevant answer in the knowledge base."

    return re.sub(
        r"\n{3,}",
        "\n\n",
        "\n\n".join(response_parts).strip(),
    )


# ============================================================
# MAIN ROUTER
# ============================================================

def route_query(
    db: Session,
    query: str,
    customer_id: int | None = None,
    session_id: str | None = None,
):
    """
    Agentic customer-support router.

    Flow:

        User Query
             ↓
        Conversation Memory
             ↓
        Intent Router
             ↓
        Controlled Tool
             ↓
        Tool Observation
             ↓
        Final Response
             ↓
        Memory Update

    The router remains controlled and deterministic while
    supporting contextual follow-up questions.
    """

    start_time = time.perf_counter()
    text = query.lower().strip()

    # ========================================================
    # 0. LOAD CONVERSATION MEMORY
    # ========================================================

    memory = get_memory(session_id)

    # =============================================
    # PERSISTENT CONVERSATION
    # =============================================

    conversation = get_or_create_conversation(
        db=db,
        customer_id=customer_id,
        session_id=session_id,
    )

    # ========================================================
    # 0.5 INPUT SCOPE GUARDRAIL
    # ========================================================

    if not is_customer_support_query(query):

        trace = [
            "Query received",
            "Conversation memory checked",
            "Input scope guardrail evaluated",
            "Query rejected as out-of-scope",
            "No controlled tool executed",
        ]

        response = (
            "I’m designed to help with customer-support "
            "requests such as orders, products, delivery, "
            "returns, refunds, warranties, and support tickets."
        )

        return build_response(
            query=query,
            agent="guardrail",
            tool=None,
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result={
                "success": False,
                "reason": "out_of_scope",
            },
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=False,
            trace=trace,
            decision={
                "intent": "out_of_scope",
                "confidence": 1.0,
                "entities": {},
                "tool": None,
                "requires_memory": False,
                "plan": [
                    "evaluate request scope",
                    "reject unsupported request",
                    "generate safe response",
                ],
            },
        )

    context_used = False

    trace = [
        "Query received",
        "Conversation memory checked",
    ]

    # ========================================================
    # 0A. AGENT DECISION / PLANNING
    # ========================================================

    decision = make_agent_decision(
        query=query,
        memory=memory,
    )

    trace.append(
        f"Agent decision created: {decision.get('intent')}"
    )

    trace.append(
        f"Decision confidence: {decision.get('confidence')}"
    )

    trace.append(
        f"Execution plan created: {decision.get('plan')}"
    )

    # ========================================================
    # 0B. CUSTOMER ID MEMORY
    # ========================================================

    if customer_id is None:
        customer_id = memory.get(
            "customer_id"
        )

    elif session_id:
        update_memory(
            session_id,
            {
                "customer_id": customer_id,
            },
        )

    # ========================================================
    # 0B. DETECT FOLLOW-UP ORDER QUESTIONS
    # ========================================================

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

    # ========================================================
    # 0C. RESOLVE ORDER FROM MEMORY
    # ========================================================

    remembered_order = memory.get(
        "last_order_number"
    )

    if (
        is_order_followup
        and remembered_order
    ):
        context_used = True

        trace.append(
            f"Previous order context found: {remembered_order}"
        )

        order_result = get_order_status(
            db=db,
            order_number=remembered_order,
        )

        trace.extend(
            [
                "Router selected: order_status",
                "Controlled tool executed: get_order_status",
                "Tool observation received",
                "Final response generated",
                "Conversation memory updated",
            ]
        )

        response = order_response(
            order_result
        )

        if order_result.get("success"):

            order = order_result.get(
                "order",
                {},
            )

            update_memory(
                session_id,
                {
                    "customer_id": customer_id,
                    "last_agent": "order_status",
                    "last_tool": "get_order_status",
                    "last_order_number": remembered_order,
                    "last_order_status": order.get(
                        "status"
                    ),
                    "last_expected_delivery": order.get(
                        "expected_delivery"
                    ),
                },
            )

        return build_response(
            query=query,
            agent="order_status",
            tool="get_order_status",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=order_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=context_used,
            trace=trace,
            decision=decision,
        )

    # ========================================================
    # 1. HUMAN ESCALATION
    # ========================================================

    if decision.get("intent") == "escalation":

        trace.append(
            "Router selected: escalation"
        )

        # ----------------------------------------------------
        # CUSTOMER ID REQUIRED
        # ----------------------------------------------------

        if customer_id is None:

            result = {
                "success": False,
                "message": (
                    "customer_id is required to escalate "
                    "this conversation to human support."
                ),
                "escalated": False,
            }

            trace.extend(
                [
                    "Controlled tool not executed",
                    "Validation response generated",
                ]
            )

            return build_response(
                query=query,
                agent="escalation",
                tool="create_support_ticket",
                db=db,
                conversation=conversation,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                result=result,
                response=result["message"],
                memory_enabled=True,
                session_id=session_id,
                customer_id=customer_id,
                context_used=False,
                trace=trace,
                decision=decision,
            )

        # ----------------------------------------------------
        # CREATE HIGH-PRIORITY ESCALATION TICKET
        # ----------------------------------------------------

        ticket_result = create_support_ticket(
            db=db,
            customer_id=customer_id,
            subject="Human support escalation",
            description=query,
            priority="high",
        )

        trace.extend(
            [
                "Controlled tool executed: create_support_ticket",
                "Tool observation received",
            ]
        )

        if ticket_result.get("success"):

            ticket = ticket_result.get(
                "ticket",
                {},
            )

            ticket_id = ticket.get("id")

            # ------------------------------------------------
            # UPDATE ESCALATION TICKET STATE
            # ------------------------------------------------

            if ticket_id is not None:

                escalation_ticket = (
                    db.query(SupportTicket)
                    .filter(
                        SupportTicket.id == ticket_id
                    )
                    .first()
                )

                if escalation_ticket:

                    now = datetime.utcnow()

                    escalation_ticket.status = (
                        "waiting_for_agent"
                    )

                    escalation_ticket.escalated_at = now

                    escalation_ticket.last_message_at = now

                    db.commit()

                    db.refresh(
                        escalation_ticket
                    )

                    ticket["status"] = (
                        escalation_ticket.status
                    )

                    ticket["escalated_at"] = (
                        escalation_ticket.escalated_at
                    )

                    ticket["last_message_at"] = (
                        escalation_ticket.last_message_at
                    )

                    trace.extend(
                        [
                            "Escalation ticket status updated to waiting_for_agent",
                            "Escalation timestamp recorded",
                            "Last message timestamp recorded",
                        ]
                    )

            response = (
                f"I've escalated your request to human support "
                f"and created support ticket #{ticket_id}. "
                f"The ticket is now waiting for a support agent "
                f"and has high priority."
            )

            update_memory(
                session_id,
                {
                    "customer_id": customer_id,
                    "last_agent": "escalation",
                    "last_tool": "create_support_ticket",
                    "last_ticket_id": ticket_id,
                    "last_ticket_status": ticket.get("status"),
                },
            )

            ticket_result["escalated"] = True

        else:

            response = ticket_result.get(
                "message",
                "I could not create the human-support escalation ticket.",
            )

            ticket_result["escalated"] = False

        trace.extend(
            [
                "Human support escalation recorded",
                "Final response generated",
                "Conversation memory updated",
            ]
        )

        return build_response(
            query=query,
            agent="escalation",
            tool="create_support_ticket",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=ticket_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=False,
            trace=trace,
            decision=decision,
        )

    # ========================================================
    # 2. CREATE SUPPORT TICKET
    # ========================================================

    if (
        decision.get("intent") == "create_ticket"
        or "create ticket" in text
        or "create a ticket" in text
        or "support ticket" in text
        or "raise a ticket" in text
        or "raise ticket" in text
        or "open a ticket" in text
        or "open ticket" in text
    ):

        trace.append(
            "Router selected: create_ticket"
        )

        # ----------------------------------------------------
        # CUSTOMER ID REQUIRED
        # ----------------------------------------------------

        if customer_id is None:

            result = {
                "success": False,
                "message": (
                    "customer_id is required to create "
                    "a support ticket."
                ),
            }

            trace.extend(
                [
                    "Controlled tool not executed",
                    "Validation response generated",
                ]
            )

            return build_response(
                query=query,
                agent="create_ticket",
                tool="create_support_ticket",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
                result=result,
                response=result["message"],
                memory_enabled=True,
                session_id=session_id,
                customer_id=customer_id,
                context_used=False,
                trace=trace,
                decision=decision,
            )

        # ----------------------------------------------------
        # DETECT PRIORITY
        # ----------------------------------------------------

        priority = "medium"

        if (
            "high priority" in text
            or "urgent" in text
            or "emergency" in text
        ):
            priority = "high"

        elif (
            "low priority" in text
            or "not urgent" in text
        ):
            priority = "low"

        # ----------------------------------------------------
        # REMOVE COMMAND WORDS
        # ----------------------------------------------------

        description = query

        patterns = [
            r"create\s+(?:a\s+)?support\s+ticket",
            r"create\s+(?:a\s+)?ticket",
            r"raise\s+(?:a\s+)?support\s+ticket",
            r"raise\s+(?:a\s+)?ticket",
            r"open\s+(?:a\s+)?support\s+ticket",
            r"open\s+(?:a\s+)?ticket",
        ]

        for pattern in patterns:

            description = re.sub(
                pattern,
                "",
                description,
                flags=re.IGNORECASE,
            )

        description = description.strip(
            " :,-."
        )

        # ----------------------------------------------------
        # NO DESCRIPTION
        # ----------------------------------------------------

        if not description:

            result = {
                "success": False,
                "message": (
                    "Please describe the issue you need "
                    "help with."
                ),
            }

            trace.extend(
                [
                    "Controlled tool not executed",
                    "Validation response generated",
                ]
            )

            return build_response(
                query=query,
                agent="create_ticket",
                tool="create_support_ticket",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
                result=result,
                response=result["message"],
                memory_enabled=True,
                session_id=session_id,
                customer_id=customer_id,
                context_used=False,
                trace=trace,
                decision=decision,
            )

        # ----------------------------------------------------
        # GENERATE SUBJECT
        # ----------------------------------------------------

        subject = description

        if len(subject) > 80:
            subject = subject[:77] + "..."

        subject = subject.capitalize()

        # ----------------------------------------------------
        # CREATE TICKET
        # ----------------------------------------------------

        ticket_result = create_support_ticket(
            db=db,
            customer_id=customer_id,
            subject=subject,
            description=description,
            priority=priority,
        )

        trace.extend(
            [
                "Controlled tool executed: create_support_ticket",
                "Tool observation received",
            ]
        )

        # ----------------------------------------------------
        # GENERATE RESPONSE
        # ----------------------------------------------------

        if ticket_result.get("success"):

            ticket = ticket_result.get(
                "ticket",
                {},
            )

            ticket_id = ticket.get(
                "id"
            )

            response = (
                f"Support ticket #{ticket_id} "
                f"has been created successfully. "
                f"Priority: {priority}. "
                f"Status: {ticket.get('status', 'open')}."
            )

            update_memory(
                session_id,
                {
                    "customer_id": customer_id,
                    "last_agent": "create_ticket",
                    "last_tool": "create_support_ticket",
                    "last_ticket_id": ticket_id,
                    "last_ticket_status": ticket.get(
                        "status"
                    ),
                },
            )

        else:

            response = ticket_result.get(
                "message",
                "The support ticket could not be created.",
            )

        trace.extend(
            [
                "Final response generated",
                "Conversation memory updated",
            ]
        )

        return build_response(
            query=query,
            agent="create_ticket",
            tool="create_support_ticket",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=ticket_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=False,
            trace=trace,
            decision=decision,
        )

    # ========================================================
    # 2. TICKET STATUS
    # ========================================================

    if (
        (decision.get("intent") == "ticket_status")
        or (
            "ticket" in text
            and (
            "status" in text
            or "check ticket" in text
            or "ticket status" in text
        )
        )
    ):

        trace.append(
            "Router selected: ticket_status"
        )

        match = re.search(
            r"\b(?:ticket\s*)?(\d+)\b",
            text,
        )

        # ----------------------------------------------------
        # USE REMEMBERED TICKET IF NO ID IS PROVIDED
        # ----------------------------------------------------

        if match:

            ticket_id = int(
                match.group(1)
            )

        elif memory.get("last_ticket_id"):

            ticket_id = int(
                memory["last_ticket_id"]
            )

            context_used = True

            trace.append(
                f"Previous ticket context found: #{ticket_id}"
            )

        else:

            result = {
                "success": False,
                "message": (
                    "Please provide your ticket ID, "
                    "for example ticket 3."
                ),
            }

            trace.extend(
                [
                    "Controlled tool not executed",
                    "Validation response generated",
                ]
            )

            return build_response(
                query=query,
                agent="ticket_status",
                tool="get_ticket_status",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
                result=result,
                response=result["message"],
                memory_enabled=True,
                session_id=session_id,
                customer_id=customer_id,
                context_used=False,
                trace=trace,
                decision=decision,
            )

        ticket_result = get_ticket_status(
            db=db,
            ticket_id=ticket_id,
        )

        trace.extend(
            [
                "Controlled tool executed: get_ticket_status",
                "Tool observation received",
            ]
        )

        if ticket_result.get("success"):

            ticket = ticket_result.get(
                "ticket",
                {},
            )

            response = (
                f"Ticket #{ticket.get('id')} is "
                f"currently {ticket.get('status')}. "
                f"Priority: {ticket.get('priority')}. "
                f"Subject: {ticket.get('subject')}."
            )

            update_memory(
                session_id,
                {
                    "customer_id": customer_id,
                    "last_agent": "ticket_status",
                    "last_tool": "get_ticket_status",
                    "last_ticket_id": ticket_id,
                    "last_ticket_status": ticket.get(
                        "status"
                    ),
                },
            )

        else:

            response = ticket_result.get(
                "message",
                "I could not retrieve the ticket status.",
            )

        trace.extend(
            [
                "Final response generated",
                "Conversation memory updated",
            ]
        )

        return build_response(
            query=query,
            agent="ticket_status",
            tool="get_ticket_status",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=ticket_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=context_used,
            trace=trace,
            decision=decision,
        )

    # ========================================================
    # 3. MULTI-STEP ORDER + POLICY
    # ========================================================

    if decision.get("intent") == "order_policy":

        trace.append(
            "Router selected: order_policy"
        )

        # ----------------------------------------------------
        # IDENTIFY ORDER
        # ----------------------------------------------------

        match = re.search(
            r"\bORD\d+\b",
            query,
            re.IGNORECASE,
        )

        if match:

            order_number = match.group(0).upper()

        elif memory.get("last_order_number"):

            order_number = memory["last_order_number"]

            context_used = True

            trace.append(
                f"Previous order context found: {order_number}"
            )

        else:

            result = {
                "success": False,
                "message": (
                    "Please provide your order number, "
                    "for example ORD1002."
                ),
            }

            trace.extend(
                [
                    "Controlled tool not executed",
                    "Validation response generated",
                ]
            )

            return build_response(
                query=query,
                agent="order_policy",
                tool="get_order_status",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
                result=result,
                response=result["message"],
                memory_enabled=True,
                session_id=session_id,
                customer_id=customer_id,
                context_used=False,
                trace=trace,
                decision=decision,
            )

        # ----------------------------------------------------
        # STEP 1: GET ORDER STATUS
        # ----------------------------------------------------

        order_result = get_order_status(
            db=db,
            order_number=order_number,
        )

        trace.extend(
            [
                "Step 1 executed: get_order_status",
                "Order observation received",
            ]
        )

        if not order_result.get("success"):

            response = order_result.get(
                "message",
                "I could not retrieve the order details.",
            )

            trace.append(
                "Multi-step execution stopped: order lookup failed"
            )

            return build_response(
                query=query,
                agent="order_policy",
                tool="get_order_status",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
                result=order_result,
                response=response,
                memory_enabled=True,
                session_id=session_id,
                customer_id=customer_id,
                context_used=context_used,
                trace=trace,
                decision=decision,
            )

        # ----------------------------------------------------
        # STEP 2: RETRIEVE RELEVANT POLICY
        # ----------------------------------------------------

        policy_query = (
            "What should a customer do if an order has "
            "passed its expected delivery date or is delayed?"
        )

        rag_result = search_knowledge_base(
            query=policy_query,
            top_k=3,
        )

        trace.extend(
            [
                "Step 2 executed: search_knowledge_base",
                "Policy observation received",
            ]
        )

        # ----------------------------------------------------
        # STEP 3: EXTRACT ORDER INFORMATION
        # ----------------------------------------------------

        order = order_result.get(
            "order",
            {},
        )

        status = order.get(
            "status",
            "unknown",
        )

        expected_delivery = order.get(
            "expected_delivery",
        )

        # ----------------------------------------------------
        # STEP 4: DETERMINE WHETHER DELIVERY IS DELAYED
        # ----------------------------------------------------

        from datetime import datetime

        is_delayed = False

        if expected_delivery:

            try:

                if isinstance(
                    expected_delivery,
                    str,
                ):
                    delivery_date = datetime.fromisoformat(
                        expected_delivery.replace(
                            "Z",
                            "",
                        )
                    )

                else:

                    delivery_date = expected_delivery

                is_delayed = (
                    delivery_date < datetime.now()
                )

            except (
                ValueError,
                TypeError,
            ):
                is_delayed = False

        trace.append(
            f"Order delay evaluation completed: delayed={is_delayed}"
        )

        # ----------------------------------------------------
        # STEP 5: GENERATE COMBINED RESPONSE
        # ----------------------------------------------------

        if is_delayed:

            response = (
                f"Order {order_number} is currently "
                f"{status}. Its expected delivery date was "
                f"{expected_delivery}, which has passed. "
                f"Based on the support policy, customers "
                f"should contact customer support when an "
                f"order has passed its expected delivery date."
            )

        else:

            response = (
                f"Order {order_number} is currently "
                f"{status}. The expected delivery date is "
                f"{expected_delivery}. Based on the available "
                f"order information, the order has not been "
                f"identified as delayed."
            )

        trace.extend(
            [
                "Order data combined with policy information",
                "Final response generated",
            ]
        )

        # ----------------------------------------------------
        # SAVE ORDER MEMORY
        # ----------------------------------------------------

        update_memory(
            session_id,
            {
                "customer_id": customer_id,
                "last_agent": "order_policy",
                "last_tool": "get_order_status",
                "last_order_number": order_number,
                "last_order_status": status,
                "last_expected_delivery": expected_delivery,
            },
        )

        trace.append(
            "Conversation memory updated"
        )

        # ----------------------------------------------------
        # RETURN MULTI-STEP RESULT
        # ----------------------------------------------------

        combined_result = {
            "success": True,
            "order": order,
            "policy": rag_result,
            "is_delayed": is_delayed,
        }

        return build_response(
            query=query,
            agent="order_policy",
            tool="get_order_status + search_knowledge_base",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=combined_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=context_used,
            trace=trace,
            decision=decision,
        )


    # ========================================================
    # 3. ORDER STATUS / TRACKING
    # ========================================================

    if (
        (decision.get("intent") == "order_status")
        or (
            "order" in text
            and (
            "status" in text
            or "where" in text
            or "track" in text
            or "delivery" in text
        )
        )
    ):

        trace.append(
            "Router selected: order_status"
        )

        match = re.search(
            r"\bORD\d+\b",
            query,
            re.IGNORECASE,
        )

        # ----------------------------------------------------
        # USE REMEMBERED ORDER IF NO ORDER NUMBER PROVIDED
        # ----------------------------------------------------

        if match:

            order_number = (
                match.group(0).upper()
            )

        elif memory.get("last_order_number"):

            order_number = memory[
                "last_order_number"
            ]

            context_used = True

            trace.append(
                f"Previous order context found: {order_number}"
            )

        else:

            result = {
                "success": False,
                "message": (
                    "Please provide your order number, "
                    "for example ORD1002."
                ),
            }

            trace.extend(
                [
                    "Controlled tool not executed",
                    "Validation response generated",
                ]
            )

            return build_response(
                query=query,
                agent="order_status",
                tool="get_order_status",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
                result=result,
                response=result["message"],
                memory_enabled=True,
                session_id=session_id,
                customer_id=customer_id,
                context_used=False,
                trace=trace,
                decision=decision,
            )

        order_result = get_order_status(
            db=db,
            order_number=order_number,
        )

        trace.extend(
            [
                "Controlled tool executed: get_order_status",
                "Tool observation received",
            ]
        )

        response = order_response(
            order_result
        )

        # ----------------------------------------------------
        # SAVE ORDER CONTEXT
        # ----------------------------------------------------

        if order_result.get("success"):

            order = order_result.get(
                "order",
                {},
            )

            update_memory(
                session_id,
                {
                    "customer_id": customer_id,
                    "last_agent": "order_status",
                    "last_tool": "get_order_status",
                    "last_order_number": order_number,
                    "last_order_status": order.get(
                        "status"
                    ),
                    "last_expected_delivery": order.get(
                        "expected_delivery"
                    ),
                },
            )

        trace.extend(
            [
                "Final response generated",
                "Conversation memory updated",
            ]
        )

        return build_response(
            query=query,
            agent="order_status",
            tool="get_order_status",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=order_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=context_used,
            trace=trace,
            decision=decision,
        )

    # ========================================================
    # 4. PRODUCT DETAILS
    # ========================================================

    if (
        decision.get("intent") == "product_details"
        or "product details" in text
        or "details of product" in text
        or "product information" in text
    ):

        trace.append(
            "Router selected: product_details"
        )

        match = re.search(
            r"\b(?:product\s*)?(\d+)\b",
            text,
        )

        if match:

            product_id = int(
                match.group(1)
            )

        elif memory.get("last_product_id"):

            product_id = int(
                memory["last_product_id"]
            )

            context_used = True

            trace.append(
                f"Previous product context found: {product_id}"
            )

        else:

            result = {
                "success": False,
                "message": (
                    "Please provide the product ID."
                ),
            }

            trace.extend(
                [
                    "Controlled tool not executed",
                    "Validation response generated",
                ]
            )

            return build_response(
                query=query,
                agent="product_details",
                tool="get_product_details",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
                result=result,
                response=result["message"],
                memory_enabled=True,
                session_id=session_id,
                customer_id=customer_id,
                context_used=False,
                trace=trace,
                decision=decision,
            )

        product_result = get_product_details(
            db=db,
            product_id=product_id,
        )

        trace.extend(
            [
                "Controlled tool executed: get_product_details",
                "Tool observation received",
            ]
        )

        response = product_response(
            product_result
        )

        if product_result.get("success"):

            update_memory(
                session_id,
                {
                    "customer_id": customer_id,
                    "last_agent": "product_details",
                    "last_tool": "get_product_details",
                    "last_product_id": product_id,
                },
            )

        trace.extend(
            [
                "Final response generated",
                "Conversation memory updated",
            ]
        )

        return build_response(
            query=query,
            agent="product_details",
            tool="get_product_details",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=product_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=context_used,
            trace=trace,
            decision=decision,
        )

    # ========================================================
    # 5. RAG / KNOWLEDGE BASE
    # ========================================================

    rag_keywords = [
        "return",
        "refund",
        "warranty",
        "shipping",
        "delivery",
        "cancelled",
        "canceled",
        "cancellation",
        "policy",
        "damaged",
        "damage",
        "eligibility",
        "eligible",
        "how long",
        "business days",
        "support",
    ]

    if (
        decision.get("intent") != "product_search"
        and any(
            keyword in text
            for keyword in rag_keywords
        )
    ):

        trace.append(
            "Router selected: rag"
        )

        rag_result = search_knowledge_base(
            query=query,
            top_k=5,
        )

        trace.extend(
            [
                "Controlled tool executed: search_knowledge_base",
                "Tool observation received",
            ]
        )

        # ====================================================
        # IMPORTANT:
        # DO NOT RETURN RAW CHUNKS DIRECTLY.
        # ====================================================

        response = format_rag_response(
            query=query,
            rag_result=rag_result,
        )

        trace.extend(
            [
                "Relevant policy sections selected",
                "Final response generated",
                "Conversation memory updated",
            ]
        )

        update_memory(
            session_id,
            {
                "customer_id": customer_id,
                "last_agent": "rag",
                "last_tool": "search_knowledge_base",
                "last_query": query,
            },
        )

        return build_response(
            query=query,
            agent="rag",
            tool="search_knowledge_base",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=rag_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=False,
            trace=trace,
            decision=decision,
        )

    # ========================================================
    # 6. PRODUCT SEARCH
    # ========================================================

    product_keywords = [
        "keyboard", "keyboards",
        "mouse", "mice",
        "laptop", "laptops",
        "monitor", "monitors",
        "webcam", "webcams",
        "headphone", "headphones",
        "earphone", "earphones", "earbuds",
        "speaker", "speakers",
        "phone", "phones", "smartphone", "smartphones",
        "tablet", "tablets",
        "charger", "chargers",
        "cable", "cables",
        "adapter", "adapters",
        "hub", "hubs", "usb", "usb-c", "usb c",
        "type-c", "type c",
        "power bank", "powerbank",
        "watch", "watches", "smartwatch", "smartwatches",
        "wearable", "wearables",
        "camera", "cameras",
        "printer", "printers",
        "router", "routers",
        "ssd", "hard drive", "hard drives", "storage",
    ]

    # The decision layer is authoritative for product-search intent.
    # Keyword matching remains as a backward-compatible fallback.
    if (
        decision.get("intent") == "product_search"
        or any(keyword in text for keyword in product_keywords)
    ):

        trace.append(
            "Router selected: product_search"
        )

        search_query = query.strip()

        # Prefer a specific catalog keyword when one is present.
        # Keep multi-word USB-C hub requests intact.
        normalized_query = (
            search_query.lower()
            .replace("usb c", "usb-c")
            .replace("type c", "type-c")
        )

        if "usb-c" in normalized_query and "hub" in normalized_query:
            search_query = "USB-C hub"
        elif "type-c" in normalized_query and "hub" in normalized_query:
            search_query = "USB-C hub"
        else:
            for keyword in product_keywords:
                if keyword in text:
                    search_query = keyword
                    break

        trace.append(
            f"Product search query: {search_query}"
        )

        product_result = search_products(
            db=db,
            query=search_query,
        )

        trace.extend(
            [
                "Controlled tool executed: search_products",
                "Tool observation received",
            ]
        )

        # ----------------------------------------------------
        # BUILD PRODUCT RESPONSE
        # ----------------------------------------------------

        if product_result.get("success"):

            products = product_result.get(
                "products",
                [],
            )

            if products:

                response = "\n".join(
                    (
                        f"{product.get('name')} — "
                        f"₹{product.get('price')} "
                        f"(Stock: {product.get('stock')})"
                    )
                    for product in products
                )

            else:

                response = (
                    "I couldn't find any matching products."
                )

        else:

            response = product_result.get(
                "message",
                "I couldn't search the products.",
            )

        # ----------------------------------------------------
        # MEMORY
        # ----------------------------------------------------

        update_memory(
            session_id,
            {
                "customer_id": customer_id,
                "last_agent": "product_search",
                "last_tool": "search_products",
                "last_product_query": search_query,
            },
        )

        trace.extend(
            [
                "Final response generated",
                "Conversation memory updated",
            ]
        )

        return build_response(
            query=query,
            agent="product_search",
            tool="search_products",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            result=product_result,
            response=response,
            memory_enabled=True,
            session_id=session_id,
            customer_id=customer_id,
            context_used=False,
            trace=trace,
            decision=decision,
        )

    # ========================================================
    # 7. DEFAULT → RAG
    # ========================================================

    trace.append(
        "Router selected: rag"
    )

    rag_result = search_knowledge_base(
        query=query,
        top_k=3,
    )

    trace.extend(
        [
            "Controlled tool executed: search_knowledge_base",
            "Tool observation received",
        ]
    )

    # Use the SAME clean RAG formatter for the default route.
    response = format_rag_response(
        query=query,
        rag_result=rag_result,
    )

    update_memory(
        session_id,
        {
            "customer_id": customer_id,
            "last_agent": "rag",
            "last_tool": "search_knowledge_base",
            "last_query": query,
        },
    )

    trace.extend(
        [
            "Relevant policy sections selected",
            "Final response generated",
            "Conversation memory updated",
        ]
    )

    return build_response(
        query=query,
        agent="rag",
        tool="search_knowledge_base",
            db=db,
            conversation=conversation,
            latency_ms=(time.perf_counter() - start_time) * 1000,
        result=rag_result,
        response=response,
        memory_enabled=True,
        session_id=session_id,
        customer_id=customer_id,
        context_used=False,
        trace=trace,
            decision=decision,
    )
