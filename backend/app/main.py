from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database.connection import engine, get_db

from app.database.models import (
    Order,
    SupportTicket,
    Product,
    User,
)

from app.rag.loader import (
    load_documents, 
    load_and_chunk_documents,
)

from app.database.models import (
    Order,
    OrderItem,
    Product,
    SupportTicket,
)

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

from app.rag.loader import (
    load_documents,
    load_and_chunk_documents,
)

from app.agent.router import route_query


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Agentic Customer Support Associate",
    description=(
        "AI-powered customer support system with "
        "ReAct, RAG, conversation memory and controlled tools."
    ),
    version="0.2.0",
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Agentic Customer Support Associate API",
        "status": "running",
        "version": "0.2.0",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


# ============================================================
# DATABASE HEALTH CHECK
# ============================================================

@app.get("/health/database")
def database_health_check():

    try:
        with engine.connect() as connection:

            result = connection.execute(
                text("SELECT 1")
            )

            value = result.scalar()

        return {
            "status": "healthy",
            "database": "connected",
            "test_result": value,
        }

    except Exception as error:

        return {
            "status": "error",
            "database": "connection_failed",
            "error": str(error),
        }


@app.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    """
    Return live statistics for the dashboard.
    """

    total_orders = db.query(Order).count()
    support_tickets = db.query(SupportTicket).count()
    total_products = db.query(Product).count()
    total_users = db.query(User).count()

    knowledge_documents = len(load_documents())
    rag_chunks = len(load_and_chunk_documents())

    return {
        "success": True,
        "stats": {
            "total_orders": total_orders,
            "support_tickets": support_tickets,
            "total_products": total_products,
            "total_users": total_users,
            "knowledge_documents": knowledge_documents,
            "rag_chunks": rag_chunks,
        },
    }


# ============================================================
# CREATE TICKET REQUEST
# ============================================================

class CreateTicketRequest(BaseModel):

    customer_id: int

    subject: str

    description: str

    priority: str = "medium"


# ============================================================
# ORDER STATUS TOOL
# ============================================================

@app.get("/tools/order-status")
def order_status(
    order_number: str,
    db: Session = Depends(get_db),
):

    return get_order_status(
        db=db,
        order_number=order_number,
    )


# ============================================================
# PRODUCT SEARCH TOOL
# ============================================================

@app.get("/tools/product-search")
def product_search(
    query: str,
    db: Session = Depends(get_db),
):

    return search_products(
        db=db,
        query=query,
    )


# ============================================================
# PRODUCT DETAILS TOOL
# ============================================================

@app.get("/tools/product-details")
def product_details(
    product_id: int,
    db: Session = Depends(get_db),
):

    return get_product_details(
        db=db,
        product_id=product_id,
    )


# ============================================================
# CREATE SUPPORT TICKET TOOL
# ============================================================

@app.post("/tools/create-ticket")
def create_ticket(
    request: CreateTicketRequest,
    db: Session = Depends(get_db),
):

    return create_support_ticket(
        db=db,
        customer_id=request.customer_id,
        subject=request.subject,
        description=request.description,
        priority=request.priority,
    )


# ============================================================
# TICKET STATUS TOOL
# ============================================================

@app.get("/tools/ticket-status")
def ticket_status(
    ticket_id: int,
    db: Session = Depends(get_db),
):

    return get_ticket_status(
        db=db,
        ticket_id=ticket_id,
    )


# ============================================================
# RAG SEARCH
# ============================================================

@app.get("/rag/search")
def rag_search(
    query: str,
    top_k: int = 3,
):

    return search_knowledge_base(
        query=query,
        top_k=top_k,
    )


# ============================================================
# KNOWLEDGE BASE
# ============================================================

@app.get("/knowledge-base")
def get_knowledge_base():
    """
    Return all knowledge-base documents for the
    Knowledge Base page.
    """

    documents = load_documents()
    chunks = load_and_chunk_documents()

    chunk_counts = {}

    for chunk in chunks:

        filename = chunk["filename"]

        chunk_counts[filename] = (
            chunk_counts.get(filename, 0) + 1
        )

    results = []

    for document in documents:

        filename = document["filename"]

        title = (
            filename
            .replace("_policy.md", "")
            .replace("_", " ")
            .title()
            + " Policy"
        )

        results.append(
            {
                "filename": filename,
                "title": title,
                "content": document["content"],
                "chunk_count": chunk_counts.get(
                    filename,
                    0,
                ),
            }
        )

    return {
        "success": True,
        "count": len(results),
        "documents": results,
        "total_chunks": len(chunks),
    }


# ============================================================
# AGENT QUERY REQUEST
# ============================================================

class AgentQueryRequest(BaseModel):

    query: str

    customer_id: int | None = None

    session_id: str | None = None


# ============================================================
# MAIN AGENT ENDPOINT
# ============================================================

@app.post("/agent/query")
def agent_query(
    request: AgentQueryRequest,
    db: Session = Depends(get_db),
):

    return route_query(
        db=db,
        query=request.query,
        customer_id=request.customer_id,
        session_id=request.session_id,
    )


# ============================================================
# ORDERS LIST
# ============================================================

@app.get("/orders")
def get_orders(
    customer_id: int | None = None,
    db: Session = Depends(get_db),
):
    """
    Return orders for the Orders page.

    If customer_id is provided, only that customer's
    orders are returned.
    """

    query = db.query(Order)

    if customer_id is not None:
        query = query.filter(
            Order.customer_id == customer_id
        )

    orders = (
        query
        .order_by(Order.order_date.desc())
        .all()
    )

    results = []

    for order in orders:

        items = (
            db.query(OrderItem, Product)
            .join(
                Product,
                OrderItem.product_id == Product.id,
            )
            .filter(
                OrderItem.order_id == order.id
            )
            .all()
        )

        order_items = []

        for item, product in items:

            order_items.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": item.quantity,
                    "unit_price": float(
                        item.unit_price
                    ),
                }
            )

        results.append(
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer_id": order.customer_id,
                "status": order.status,
                "order_date": (
                    order.order_date.isoformat()
                    if order.order_date
                    else None
                ),
                "expected_delivery": (
                    order.expected_delivery.isoformat()
                    if order.expected_delivery
                    else None
                ),
                "total_amount": float(
                    order.total_amount
                ),
                "items": order_items,
            }
        )

    return {
        "success": True,
        "count": len(results),
        "orders": results,
    }


# ============================================================
# TICKETS LIST
# ============================================================

@app.get("/tickets")
def get_tickets(
    customer_id: int | None = None,
    db: Session = Depends(get_db),
):
    """
    Return support tickets for the Tickets page.

    If customer_id is provided, only that customer's
    tickets are returned.
    """

    query = db.query(SupportTicket)

    if customer_id is not None:
        query = query.filter(
            SupportTicket.customer_id == customer_id
        )

    tickets = (
        query
        .order_by(SupportTicket.created_at.desc())
        .all()
    )

    results = []

    for ticket in tickets:

        results.append(
            {
                "id": ticket.id,
                "customer_id": ticket.customer_id,
                "subject": ticket.subject,
                "description": ticket.description,
                "priority": ticket.priority,
                "status": ticket.status,
                "assigned_to": ticket.assigned_to,
                "created_at": (
                    ticket.created_at.isoformat()
                    if ticket.created_at
                    else None
                ),
                "resolved_at": (
                    ticket.resolved_at.isoformat()
                    if ticket.resolved_at
                    else None
                ),
            }
        )

    return {
        "success": True,
        "count": len(results),
        "tickets": results,
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
):
    """
    Return real-time dashboard statistics
    from PostgreSQL and the RAG knowledge base.
    """

    # --------------------------------------------------------
    # ORDER COUNTS
    # --------------------------------------------------------

    total_orders = (
        db.query(func.count(Order.id))
        .scalar()
        or 0
    )

    order_status_rows = (
        db.query(
            Order.status,
            func.count(Order.id),
        )
        .group_by(Order.status)
        .all()
    )

    order_statuses = {}

    for status, count in order_status_rows:

        status_name = (
            status.lower()
            if status
            else "unknown"
        )

        order_statuses[status_name] = count

    # --------------------------------------------------------
    # TICKET COUNTS
    # --------------------------------------------------------

    total_tickets = (
        db.query(func.count(SupportTicket.id))
        .scalar()
        or 0
    )

    ticket_status_rows = (
        db.query(
            SupportTicket.status,
            func.count(SupportTicket.id),
        )
        .group_by(SupportTicket.status)
        .all()
    )

    ticket_statuses = {}

    for status, count in ticket_status_rows:

        status_name = (
            status.lower()
            if status
            else "unknown"
        )

        ticket_statuses[status_name] = count

    # --------------------------------------------------------
    # KNOWLEDGE BASE
    # --------------------------------------------------------

    documents = load_documents()
    chunks = load_and_chunk_documents()

    total_documents = len(documents)

    total_chunks = len(chunks)

    # --------------------------------------------------------
    # RETURN DASHBOARD DATA
    # --------------------------------------------------------

    return {
        "success": True,

        "agent": {
            "status": "online",
            "memory": "active",
            "rag": "active",
        },

        "summary": {
            "total_orders": total_orders,
            "total_tickets": total_tickets,
            "total_documents": total_documents,
            "total_chunks": total_chunks,
        },

        "orders": {
            "total": total_orders,
            "statuses": order_statuses,
        },

        "tickets": {
            "total": total_tickets,
            "statuses": ticket_statuses,
        },

        "knowledge_base": {
            "documents": total_documents,
            "chunks": total_chunks,
            "retrieval": "Semantic RAG",
        },
    }