from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database.connection import engine, get_db
from app.auth import create_access_token, hash_password, verify_password
from app.dependencies import get_current_user, require_roles

from app.database.models import (
    Order,
    OrderItem,
    Product,
    SupportTicket,
    User,
)

from app.rag.loader import (
    load_documents,
    load_and_chunk_documents,
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
            result = connection.execute(text("SELECT 1"))
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


# ============================================================
# AUTHENTICATION
# ============================================================

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new customer account.

    Public registration always creates a customer.
    Users cannot register themselves as admin or support_agent.
    """

    email = request.email.strip().lower()
    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required.",
        )

    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(request.password),
        role="customer",
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user.id,
        user.role,
    )

    return {
        "success": True,
        "message": "Customer account created successfully.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }


@app.post("/auth/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate a user and return a JWT access token.
    """

    email = request.email.strip().lower()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if (
        not user
        or not user.is_active
        or not verify_password(
            request.password,
            user.password_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    token = create_access_token(
        user.id,
        user.role,
    )

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        },
    }


@app.get("/auth/me")
def auth_me(
    current_user: User = Depends(get_current_user),
):
    """
    Return the authenticated user's identity and role.
    """

    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
            "is_active": current_user.is_active,
        },
    }


# ============================================================
# DASHBOARD STATS
# ============================================================

@app.get("/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("support_agent", "admin")
    ),
):
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
    current_user: User = Depends(get_current_user),
):

    result = get_order_status(
        db=db,
        order_number=order_number,
    )

    if current_user.role == "customer" and result.get("success"):

        order = result.get("order", {})

        if order.get("customer_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own orders.",
            )

    return result


# ============================================================
# PRODUCT SEARCH TOOL
# ============================================================

@app.get("/tools/product-search")
def product_search(
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    """
    Create a support ticket.

    SECURITY RULE:

    Customer:
        The customer_id from the request is completely ignored.
        The ticket ALWAYS belongs to the authenticated customer.

    Support Agent / Admin:
        They may create a ticket for a specified customer_id.
    """

    if current_user.role == "customer":

        # IMPORTANT:
        # Never trust request.customer_id for a customer.
        # Always use the authenticated JWT identity.
        actual_customer_id = current_user.id

    elif current_user.role in {"support_agent", "admin"}:

        actual_customer_id = request.customer_id

    else:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create support tickets.",
        )

    return create_support_ticket(
        db=db,
        customer_id=actual_customer_id,
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
    current_user: User = Depends(get_current_user),
):

    result = get_ticket_status(
        db=db,
        ticket_id=ticket_id,
    )

    if current_user.role == "customer" and result.get("success"):

        ticket = result.get("ticket", {})

        if ticket.get("customer_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own tickets.",
            )

    return result


# ============================================================
# RAG SEARCH
# ============================================================

@app.get("/rag/search")
def rag_search(
    query: str,
    top_k: int = 3,
    current_user: User = Depends(get_current_user),
):

    return search_knowledge_base(
        query=query,
        top_k=top_k,
    )


# ============================================================
# KNOWLEDGE BASE
# ============================================================

@app.get("/knowledge-base")
def get_knowledge_base(
    current_user: User = Depends(get_current_user),
):
    """
    Return all knowledge-base documents.
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
    current_user: User = Depends(get_current_user),
):
    """
    Main AI customer-support endpoint.

    Customers are always bound to their authenticated user ID.
    Support agents and admins may specify a customer ID.
    """

    if current_user.role == "customer":
        actual_customer_id = current_user.id

    else:
        actual_customer_id = request.customer_id

    return route_query(
        db=db,
        query=request.query,
        customer_id=actual_customer_id,
        session_id=request.session_id,
    )


# ============================================================
# ORDERS LIST
# ============================================================

@app.get("/orders")
def get_orders(
    customer_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return orders for the Orders page.

    Customers can ONLY see their own orders.

    Support agents and admins can optionally filter
    orders by customer_id.
    """

    query = db.query(Order)

    if current_user.role == "customer":

        query = query.filter(
            Order.customer_id == current_user.id
        )

    elif customer_id is not None:

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
    current_user: User = Depends(get_current_user),
):
    """
    Return support tickets for the Tickets page.

    Customers can ONLY see their own tickets.

    Support agents and admins can optionally filter
    tickets by customer_id.
    """

    query = db.query(SupportTicket)

    if current_user.role == "customer":

        query = query.filter(
            SupportTicket.customer_id == current_user.id
        )

    elif customer_id is not None:

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
    current_user: User = Depends(
        require_roles("support_agent", "admin")
    ),
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

    for order_status_value, count in order_status_rows:

        status_name = (
            order_status_value.lower()
            if order_status_value
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

    for ticket_status_value, count in ticket_status_rows:

        status_name = (
            ticket_status_value.lower()
            if ticket_status_value
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